# -*- coding: utf-8 -*-
"""
전략 실행기
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
from enum import Enum

from src.core.interfaces.strategy import Signal, MarketData
from .base import BaseStrategy, StrategyContext


class StrategyState(Enum):
    """전략 실행 상태"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class StrategyRunner:
    """전략 실행기"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        context: StrategyContext
    ):
        """
        전략 실행기 초기화
        
        Args:
            strategy: 실행할 전략
            context: 전략 실행 컨텍스트
        """
        self.strategy = strategy
        self.context = context
        self.logger = logging.getLogger(__name__)
        
        # 실행 상태
        self.state = StrategyState.IDLE
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # 통계
        self.total_data_points = 0
        self.total_signals = 0
        self.total_orders = 0
        
        # 제어
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._error: Optional[Exception] = None
    
    async def run(self, data_stream: AsyncIterator[MarketData]) -> Dict[str, Any]:
        """
        전략 실행
        
        Args:
            data_stream: 시장 데이터 스트림
            
        Returns:
            실행 결과
        """
        try:
            self.state = StrategyState.INITIALIZING
            self.start_time = datetime.now()
            self._stop_event.clear()
            self._pause_event.clear()
            
            # 전략 초기화
            await self.strategy.initialize(self.context)
            self.logger.info(f"Strategy {self.strategy.name} initialized")
            
            self.state = StrategyState.RUNNING
            
            # 데이터 스트림 처리
            async for data in data_stream:
                # 중지 확인
                if self._stop_event.is_set():
                    break
                
                # 일시정지 확인
                if self._pause_event.is_set():
                    self.state = StrategyState.PAUSED
                    await self._pause_event.wait()
                    self.state = StrategyState.RUNNING
                
                # 데이터 처리
                await self._process_data(data)
                self.total_data_points += 1
            
            # 마감 처리
            await self.strategy.on_day_end()
            
            self.state = StrategyState.STOPPED
            self.end_time = datetime.now()
            
            self.logger.info(f"Strategy {self.strategy.name} completed")
            
        except Exception as e:
            self._error = e
            self.state = StrategyState.ERROR
            self.end_time = datetime.now()
            self.logger.exception(f"Strategy {self.strategy.name} failed: {e}")
            raise
        
        return self.get_execution_summary()
    
    async def stop(self, timeout: float = 10.0):
        """
        전략 실행 중지
        
        Args:
            timeout: 중지 대기 시간 (초)
        """
        self.logger.info(f"Stopping strategy {self.strategy.name}")
        self.state = StrategyState.STOPPING
        self._stop_event.set()
        
        # 일시정지 중이면 해제
        if self._pause_event.is_set():
            self._pause_event.clear()
        
        # 중지 완료 대기
        try:
            await asyncio.wait_for(self._wait_for_stop(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Strategy {self.strategy.name} stop timeout")
    
    def pause(self):
        """전략 실행 일시정지"""
        if self.state == StrategyState.RUNNING:
            self._pause_event.set()
            self.logger.info(f"Strategy {self.strategy.name} paused")
    
    def resume(self):
        """전략 실행 재개"""
        if self.state == StrategyState.PAUSED:
            self._pause_event.clear()
            self.logger.info(f"Strategy {self.strategy.name} resumed")
    
    def get_state(self) -> StrategyState:
        """현재 실행 상태"""
        return self.state
    
    def get_statistics(self) -> Dict[str, Any]:
        """실행 통계"""
        return {
            "strategy_name": self.strategy.name,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self._get_duration(),
            "total_data_points": self.total_data_points,
            "total_signals": self.total_signals,
            "total_orders": self.total_orders,
            "error": str(self._error) if self._error else None
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """실행 요약"""
        return {
            **self.get_statistics(),
            "strategy_statistics": self.strategy.get_statistics(),
            "context_summary": self._get_context_summary()
        }
    
    async def _process_data(self, data: MarketData):
        """데이터 처리"""
        try:
            # 신호 생성
            signals = await self.strategy.on_data(data)
            self.total_signals += len(signals)
            
            # 신호 처리
            for signal in signals:
                await self._process_signal(signal)
                
        except Exception as e:
            self.logger.error(f"Error processing data for {data.symbol}: {e}")
            raise
    
    async def _process_signal(self, signal: Signal):
        """신호 처리"""
        try:
            # 리스크 검사
            if not await self._check_risk(signal):
                self.logger.debug(f"Signal rejected by risk check: {signal}")
                return
            
            # 주문 생성
            order = await self._create_order_from_signal(signal)
            
            if order:
                # 주문 실행 (모의)
                result = await self._execute_order(order)
                self.total_orders += 1
                
                if result:
                    await self.strategy.on_order_filled(result)
                    self.logger.debug(f"Order executed: {result}")
                
        except Exception as e:
            self.logger.error(f"Error processing signal: {e}")
            raise
    
    async def _check_risk(self, signal: Signal) -> bool:
        """리스크 검사"""
        try:
            # 기본 리스크 검사
            
            # 1. 포지션 크기 확인
            current_positions = self.context.get_current_positions()
            if len(current_positions) >= 10:  # 최대 10개 포지션
                return False
            
            # 2. 자본 확인
            account_value = self.context.get_account_value()
            cash_balance = self.context.get_cash_balance()
            
            if cash_balance < account_value * 0.05:  # 최소 5% 현금 유지
                return False
            
            # 3. 동일 종목 중복 확인
            if signal.symbol in current_positions:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Risk check error: {e}")
            return False
    
    async def _create_order_from_signal(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """신호에서 주문 생성"""
        try:
            from src.core.interfaces.strategy import SignalType
            
            if signal.signal_type == SignalType.HOLD:
                return None
            
            # 주문 수량 계산
            account_value = self.context.get_account_value()
            position_size = account_value * 0.1  # 계좌의 10%
            
            if signal.price:
                quantity = int(position_size / signal.price)
            else:
                quantity = 100  # 기본 수량
            
            if quantity <= 0:
                return None
            
            # 주문 생성
            order = {
                "symbol": signal.symbol,
                "side": "buy" if signal.signal_type == SignalType.BUY else "sell",
                "quantity": quantity,
                "order_type": "market",
                "price": signal.price,
                "timestamp": signal.timestamp,
                "signal_strength": signal.strength,
                "reason": signal.reason
            }
            
            return order
            
        except Exception as e:
            self.logger.error(f"Order creation error: {e}")
            return None
    
    async def _execute_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """주문 실행 (모의)"""
        try:
            # 실제 환경에서는 order_manager 사용
            # 백테스트에서는 즉시 체결 시뮬레이션
            
            filled_order = {
                **order,
                "order_id": f"ORDER_{self.total_orders + 1}",
                "status": "filled",
                "filled_quantity": order["quantity"],
                "filled_price": order["price"] or 50000,  # 기본 가격
                "commission": order["quantity"] * 0.0015,  # 0.15% 수수료
                "filled_at": datetime.now()
            }
            
            # 포트폴리오 업데이트 (실제로는 portfolio_manager가 처리)
            await self._update_portfolio(filled_order)
            
            return filled_order
            
        except Exception as e:
            self.logger.error(f"Order execution error: {e}")
            return None
    
    async def _update_portfolio(self, filled_order: Dict[str, Any]):
        """포트폴리오 업데이트 (모의)"""
        # 실제로는 PortfolioManager가 처리
        pass
    
    async def _wait_for_stop(self):
        """중지 완료 대기"""
        while self.state not in [StrategyState.STOPPED, StrategyState.ERROR]:
            await asyncio.sleep(0.1)
    
    def _get_duration(self) -> Optional[float]:
        """실행 시간 계산 (초)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    def _get_context_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약"""
        return {
            "account_value": self.context.get_account_value(),
            "cash_balance": self.context.get_cash_balance(),
            "position_count": len(self.context.get_current_positions()),
            "trade_count": self.context.trade_count,
            "winning_trades": self.context.winning_trades,
            "losing_trades": self.context.losing_trades,
            "win_rate": self.context.winning_trades / max(1, self.context.trade_count)
        }


class StrategyScheduler:
    """전략 스케줄러 - 여러 전략 병렬 실행"""
    
    def __init__(self):
        """스케줄러 초기화"""
        self.logger = logging.getLogger(__name__)
        self.runners: Dict[str, StrategyRunner] = {}
        self.running = False
    
    def add_strategy(self, name: str, runner: StrategyRunner):
        """전략 추가"""
        self.runners[name] = runner
        self.logger.info(f"Strategy {name} added to scheduler")
    
    def remove_strategy(self, name: str):
        """전략 제거"""
        if name in self.runners:
            del self.runners[name]
            self.logger.info(f"Strategy {name} removed from scheduler")
    
    async def run_all(self, data_streams: Dict[str, AsyncIterator[MarketData]]) -> Dict[str, Any]:
        """모든 전략 실행"""
        self.running = True
        results = {}
        
        try:
            # 모든 전략을 병렬로 실행
            tasks = []
            for name, runner in self.runners.items():
                if name in data_streams:
                    task = asyncio.create_task(
                        runner.run(data_streams[name]),
                        name=f"strategy_{name}"
                    )
                    tasks.append((name, task))
            
            # 모든 작업 완료 대기
            for name, task in tasks:
                try:
                    result = await task
                    results[name] = result
                except Exception as e:
                    self.logger.error(f"Strategy {name} failed: {e}")
                    results[name] = {"error": str(e)}
            
        except Exception as e:
            self.logger.exception(f"Scheduler error: {e}")
            raise
        finally:
            self.running = False
        
        return results
    
    async def stop_all(self, timeout: float = 30.0):
        """모든 전략 중지"""
        if not self.running:
            return
        
        self.logger.info("Stopping all strategies")
        
        # 모든 전략에 중지 신호
        stop_tasks = []
        for name, runner in self.runners.items():
            task = asyncio.create_task(runner.stop(timeout / len(self.runners)))
            stop_tasks.append(task)
        
        # 모든 중지 완료 대기
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.running = False
        self.logger.info("All strategies stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태"""
        return {
            "running": self.running,
            "strategy_count": len(self.runners),
            "strategies": {
                name: runner.get_statistics()
                for name, runner in self.runners.items()
            }
        }