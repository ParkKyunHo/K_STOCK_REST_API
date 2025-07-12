# -*- coding: utf-8 -*-
"""
백테스트 엔진 구현
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

from src.domain.backtest.models import BacktestConfig, BacktestResult, BacktestStatus
from src.core.models.domain import Portfolio, Transaction, TransactionType
from src.core.models.market_data import MarketData, Quote, OHLCV
from src.core.interfaces.strategy import IStrategy
from src.core.interfaces.market_data import IMarketDataProvider


@dataclass
class BacktestEvent:
    """백테스트 이벤트"""
    timestamp: datetime
    event_type: str
    data: Any
    priority: int = 0


@dataclass 
class TradeSignal:
    """거래 신호"""
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    price: Optional[Decimal] = None
    timestamp: Optional[datetime] = None


class BacktestEngine:
    """이벤트 기반 백테스트 엔진"""
    
    def __init__(
        self,
        config: BacktestConfig,
        strategy: IStrategy,
        data_provider: IMarketDataProvider,
        portfolio_manager: Optional[Any] = None
    ):
        self.config = config
        self.strategy = strategy
        self.data_provider = data_provider
        self.portfolio_manager = portfolio_manager
        
        # 상태 관리
        self.status = BacktestStatus.PENDING
        self.current_date = config.start_date
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # 결과 추적
        self.transactions: List[Transaction] = []
        self.daily_returns: List[Decimal] = []
        self.processed_events = 0
        
        # 포트폴리오 초기화
        self.portfolio = Portfolio(
            account_id="BACKTEST",
            initial_capital=float(config.initial_capital)
        )
        
        # 콜백
        self.callbacks: Dict[str, List[Callable]] = {
            "on_trade": [],
            "on_portfolio_update": [],
            "on_data_update": [],
            "on_error": []
        }
        
        # 로거
        self.logger = logging.getLogger(__name__)
        
        # 성과 추적
        self.daily_portfolio_values: List[Decimal] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    async def run(self) -> BacktestResult:
        """백테스트 실행"""
        try:
            self.logger.info(f"Starting backtest: {self.config.start_date} to {self.config.end_date}")
            self.status = BacktestStatus.RUNNING
            self.start_time = datetime.now()
            
            # 전략 초기화
            await self.strategy.initialize()
            
            # 데이터 스트림 시작
            await self._start_data_stream()
            
            # 이벤트 루프 실행
            await self._run_event_loop()
            
            # 백테스트 완료
            self.status = BacktestStatus.COMPLETED
            self.end_time = datetime.now()
            
            # 결과 생성
            result = self._create_result()
            
            self.logger.info(f"Backtest completed. Total trades: {len(self.transactions)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Backtest failed: {str(e)}")
            self.status = BacktestStatus.FAILED
            self.end_time = datetime.now()
            await self._handle_error(e)
            raise
    
    async def _start_data_stream(self):
        """데이터 스트림 시작"""
        try:
            # 히스토리 데이터 로드
            symbols = await self.strategy.get_universe()
            
            for symbol in symbols:
                async for data_batch in self.data_provider.get_historical_data(
                    symbol=symbol,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date
                ):
                    for data_point in data_batch:
                        event = BacktestEvent(
                            timestamp=data_point.timestamp,
                            event_type="market_data",
                            data=data_point
                        )
                        await self.event_queue.put(event)
            
            # 종료 이벤트
            end_event = BacktestEvent(
                timestamp=self.config.end_date,
                event_type="end",
                data=None
            )
            await self.event_queue.put(end_event)
            
        except Exception as e:
            self.logger.error(f"Failed to start data stream: {str(e)}")
            raise
    
    async def _run_event_loop(self):
        """메인 이벤트 루프"""
        while True:
            try:
                # 이벤트 가져오기 (타임아웃 설정)
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=30.0
                )
                
                # 종료 조건 확인
                if event.event_type == "end":
                    break
                
                # 이벤트 처리
                await self._process_event(event)
                self.processed_events += 1
                
                # 큐 완료 표시
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                self.logger.warning("Event loop timeout - no events received")
                break
            except Exception as e:
                self.logger.error(f"Error in event loop: {str(e)}")
                await self._handle_error(e)
                break
    
    async def _process_event(self, event: BacktestEvent):
        """개별 이벤트 처리"""
        try:
            if event.event_type == "market_data":
                await self._process_market_data(event.data)
            elif event.event_type == "trade_signal":
                await self._process_trade_signal(event.data)
            else:
                self.logger.warning(f"Unknown event type: {event.event_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_type}: {str(e)}")
            raise
    
    async def _process_market_data(self, data: MarketData):
        """시장 데이터 처리"""
        try:
            # 현재 날짜 업데이트
            if data.timestamp.date() != self.current_date.date():
                await self._process_end_of_day()
                self.current_date = data.timestamp
            
            # 전략에 데이터 전달
            signals = await self.strategy.on_data(data)
            
            # 거래 신호 처리
            if signals:
                for signal in signals:
                    await self._execute_trade_signal(signal)
            
            # 콜백 호출
            await self._trigger_callbacks("on_data_update", data)
            
        except Exception as e:
            self.logger.error(f"Failed to process market data: {str(e)}")
            raise
    
    async def _execute_trade_signal(self, signal: TradeSignal):
        """거래 신호 실행"""
        try:
            # 거래 유효성 검증
            if not self._validate_trade_signal(signal):
                return
            
            # 거래 비용 계산
            trade_cost = self._calculate_trade_cost(signal)
            
            # 거래 실행
            if signal.action.upper() == "BUY":
                await self._execute_buy_order(signal, trade_cost)
            elif signal.action.upper() == "SELL":
                await self._execute_sell_order(signal, trade_cost)
            
        except Exception as e:
            self.logger.error(f"Failed to execute trade signal: {str(e)}")
            await self._handle_error(e)
    
    async def _execute_buy_order(self, signal: TradeSignal, trade_cost: Dict[str, Decimal]):
        """매수 주문 실행"""
        total_cost = trade_cost["total_cost"]
        
        # 현금 충분성 확인
        if Decimal(str(self.portfolio.cash)) < total_cost:
            self.logger.warning(f"Insufficient cash for buy order: {signal.symbol}")
            return
        
        # 포지션 추가
        price = float(signal.price or trade_cost["execution_price"])
        self.portfolio.add_position(
            symbol=signal.symbol,
            quantity=signal.quantity,
            price=price,
            commission=float(trade_cost["commission"])
        )
        
        # 거래 기록
        transaction = Transaction(
            symbol=signal.symbol,
            transaction_type=TransactionType.BUY,
            quantity=signal.quantity,
            price=price,
            commission=float(trade_cost["commission"]),
            tax=float(trade_cost["tax"])
        )
        self.transactions.append(transaction)
        
        # 콜백 호출
        await self._trigger_callbacks("on_trade", transaction)
        await self._trigger_callbacks("on_portfolio_update", self.portfolio)
        
        self.logger.info(f"Buy order executed: {signal.symbol} x{signal.quantity} @ {price}")
    
    async def _execute_sell_order(self, signal: TradeSignal, trade_cost: Dict[str, Decimal]):
        """매도 주문 실행"""
        # 포지션 확인
        if signal.symbol not in self.portfolio.positions:
            self.logger.warning(f"No position to sell: {signal.symbol}")
            return
        
        position = self.portfolio.positions[signal.symbol]
        if position.quantity < signal.quantity:
            self.logger.warning(f"Insufficient quantity to sell: {signal.symbol}")
            return
        
        # 매도 실행
        price = float(signal.price or trade_cost["execution_price"])
        self.portfolio.close_position(
            symbol=signal.symbol,
            price=price,
            commission=float(trade_cost["commission"]),
            tax=float(trade_cost["tax"])
        )
        
        # 거래 기록
        transaction = Transaction(
            symbol=signal.symbol,
            transaction_type=TransactionType.SELL,
            quantity=signal.quantity,
            price=price,
            commission=float(trade_cost["commission"]),
            tax=float(trade_cost["tax"])
        )
        self.transactions.append(transaction)
        
        # 콜백 호출
        await self._trigger_callbacks("on_trade", transaction)
        await self._trigger_callbacks("on_portfolio_update", self.portfolio)
        
        self.logger.info(f"Sell order executed: {signal.symbol} x{signal.quantity} @ {price}")
    
    def _validate_trade_signal(self, signal: TradeSignal) -> bool:
        """거래 신호 유효성 검증"""
        if not signal.symbol:
            self.logger.error("Trade signal missing symbol")
            return False
        
        if signal.action not in ["BUY", "SELL"]:
            self.logger.error(f"Invalid trade action: {signal.action}")
            return False
        
        if signal.quantity <= 0:
            self.logger.error(f"Invalid quantity: {signal.quantity}")
            return False
        
        return True
    
    def _calculate_trade_cost(self, signal: TradeSignal) -> Dict[str, Decimal]:
        """거래 비용 계산"""
        price = signal.price or Decimal("0")  # 실제로는 현재가를 사용
        notional = price * signal.quantity
        
        # 슬리피지 적용
        slippage = notional * self.config.slippage_rate
        execution_price = price + (slippage / signal.quantity)
        
        # 수수료 계산
        commission = notional * self.config.commission_rate
        
        # 세금 계산 (매도시만)
        tax = Decimal("0")
        if signal.action.upper() == "SELL":
            tax = notional * self.config.tax_rate
        
        # 총 비용
        if signal.action.upper() == "BUY":
            total_cost = notional + commission + slippage
        else:  # SELL
            total_cost = notional - commission - tax - slippage
        
        return {
            "execution_price": execution_price,
            "notional": notional,
            "commission": commission,
            "tax": tax,
            "slippage": slippage,
            "total_cost": total_cost
        }
    
    async def _process_end_of_day(self):
        """일일 마감 처리"""
        try:
            # 포트폴리오 가치 계산 (현재가 정보 필요)
            current_value = Decimal(str(self.portfolio.cash))
            for symbol, position in self.portfolio.positions.items():
                # 실제로는 현재가를 가져와야 함
                position_value = Decimal(str(position.average_price * position.quantity))
                current_value += position_value
            
            self.daily_portfolio_values.append(current_value)
            
            # 일일 수익률 계산
            if len(self.daily_portfolio_values) > 1:
                prev_value = self.daily_portfolio_values[-2]
                daily_return = (current_value - prev_value) / prev_value
                self.daily_returns.append(daily_return)
            
            self.logger.debug(f"End of day: {self.current_date.date()}, Portfolio value: {current_value}")
            
        except Exception as e:
            self.logger.error(f"Failed to process end of day: {str(e)}")
            raise
    
    def _create_result(self) -> BacktestResult:
        """백테스트 결과 생성"""
        return BacktestResult(
            config=self.config,
            status=self.status,
            start_time=self.start_time or datetime.now(),
            end_time=self.end_time or datetime.now(),
            final_portfolio=self.portfolio,
            transactions=self.transactions,
            daily_returns=self.daily_returns,
            metadata={
                "strategy_name": getattr(self.strategy, 'name', 'Unknown'),
                "strategy_version": getattr(self.strategy, 'version', '1.0.0'),
                "processed_events": self.processed_events,
                "total_trades": len(self.transactions)
            }
        )
    
    async def _trigger_callbacks(self, event_type: str, data: Any):
        """콜백 트리거"""
        callbacks = self.callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Callback error ({event_type}): {str(e)}")
    
    async def _handle_error(self, error: Exception):
        """에러 처리"""
        await self._trigger_callbacks("on_error", error)
    
    def register_callback(self, event_type: str, callback: Callable):
        """콜백 등록"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def get_status(self) -> BacktestStatus:
        """현재 상태 반환"""
        return self.status
    
    def get_progress(self) -> Dict[str, Any]:
        """진행 상황 반환"""
        if self.config.start_date >= self.config.end_date:
            progress_pct = 100.0
        else:
            total_days = (self.config.end_date - self.config.start_date).days
            elapsed_days = (self.current_date - self.config.start_date).days
            progress_pct = min(100.0, (elapsed_days / total_days) * 100)
        
        return {
            "status": self.status.value,
            "progress_percentage": progress_pct,
            "current_date": self.current_date,
            "processed_events": self.processed_events,
            "total_trades": len(self.transactions),
            "current_portfolio_value": Decimal(str(self.portfolio.cash))
        }
    
    async def pause(self):
        """백테스트 일시정지"""
        # 실제 구현에서는 상태 변경 및 이벤트 루프 제어
        pass
    
    async def resume(self):
        """백테스트 재개"""
        # 실제 구현에서는 상태 변경 및 이벤트 루프 재시작
        pass
    
    async def cancel(self):
        """백테스트 취소"""
        self.status = BacktestStatus.CANCELLED
        # 이벤트 큐 정리
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
                self.event_queue.task_done()
            except asyncio.QueueEmpty:
                break