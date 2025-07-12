# -*- coding: utf-8 -*-
"""
전략 베이스 클래스 및 전략 실행 컨텍스트
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from decimal import Decimal

import pandas as pd

from src.core.interfaces.strategy import IStrategy, Signal, MarketData
from src.core.interfaces import IMarketDataProvider
from src.core.models.domain import Portfolio


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "parameters": self.parameters,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class StrategyContext:
    """전략 실행 컨텍스트"""
    portfolio: Portfolio
    data_provider: IMarketDataProvider
    logger: logging.Logger
    
    # 백테스트 설정
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    commission_rate: Decimal = Decimal("0.00015")
    slippage_rate: Decimal = Decimal("0.0001")
    
    # 실행 모드
    is_live: bool = False
    is_paper_trading: bool = False
    
    # 성과 추적
    current_date: Optional[datetime] = None
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    def get_current_positions(self) -> Dict[str, Any]:
        """현재 포지션 조회"""
        return {p.symbol: p for p in self.portfolio.positions.values()}
    
    def get_account_value(self) -> float:
        """계좌 가치 조회"""
        return self.portfolio.get_total_value()
    
    def get_cash_balance(self) -> float:
        """현금 잔고 조회"""
        return self.portfolio.cash
    
    async def get_historical_data(
        self,
        symbol: str,
        lookback_days: int,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """과거 데이터 조회"""
        from datetime import timedelta
        
        if self.current_date:
            end_date = self.current_date
        else:
            end_date = datetime.now()
            
        start_date = end_date - timedelta(days=lookback_days)
        
        data = await self.data_provider.get_ohlcv(
            symbol, interval, start_date, end_date
        )
        
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    def log_trade(self, signal: Signal, success: bool = True):
        """거래 로그 기록"""
        self.trade_count += 1
        if success:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            
        self.logger.info(
            f"Trade #{self.trade_count}: {signal.signal_type.value} "
            f"{signal.symbol} @ {signal.price} - {'SUCCESS' if success else 'FAILED'}"
        )


class BaseStrategy(IStrategy):
    """전략 베이스 클래스"""
    
    def __init__(self, config: StrategyConfig):
        """
        전략 초기화
        
        Args:
            config: 전략 설정
        """
        self.config = config
        self.context: Optional[StrategyContext] = None
        self.logger: Optional[logging.Logger] = None
        self.initialized = False
        
        # 전략 상태
        self.data_history: List[MarketData] = []
        self.signals_history: List[Signal] = []
        self.current_positions: Dict[str, Any] = {}
        
        # 성과 추적
        self.total_signals = 0
        self.executed_trades = 0
        
    @property
    def name(self) -> str:
        """전략 이름"""
        return self.config.name
    
    @property
    def version(self) -> str:
        """전략 버전"""
        return self.config.version
    
    @property
    def description(self) -> str:
        """전략 설명"""
        return self.config.description
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """전략 파라미터"""
        return self.config.parameters
    
    async def initialize(self, context: StrategyContext) -> None:
        """전략 초기화"""
        self.context = context
        self.logger = context.logger
        
        # 파라미터 검증
        if not self.validate_parameters():
            raise ValueError(f"Invalid parameters for strategy {self.name}")
        
        # 커스텀 초기화
        await self.on_initialize()
        
        self.initialized = True
        self.logger.info(f"Strategy {self.name} v{self.version} initialized")
    
    async def on_data(self, data: MarketData) -> List[Signal]:
        """데이터 수신 시 호출"""
        if not self.initialized:
            raise RuntimeError("Strategy not initialized")
        
        # 데이터 히스토리 업데이트
        self.data_history.append(data)
        self._trim_history()
        
        # 컨텍스트 업데이트
        if self.context:
            self.context.current_date = data.timestamp
            self.current_positions = self.context.get_current_positions()
        
        # 신호 생성
        signals = await self.generate_signals(data)
        
        # 신호 검증 및 후처리
        validated_signals = []
        for signal in signals:
            if self._validate_signal(signal):
                validated_signals.append(signal)
                self.signals_history.append(signal)
                self.total_signals += 1
        
        if validated_signals:
            self.logger.debug(f"Generated {len(validated_signals)} signals for {data.symbol}")
        
        return validated_signals
    
    async def on_order_filled(self, order: Any) -> None:
        """주문 체결 시 호출"""
        if not self.initialized:
            return
            
        self.executed_trades += 1
        
        if self.context:
            # 성과 추적
            success = hasattr(order, 'status') and order.status == 'filled'
            
            # 임시 신호 생성 (실제로는 매칭되는 신호를 찾아야 함)
            from src.core.interfaces.strategy import SignalType
            signal = Signal(
                timestamp=datetime.now(),
                symbol=order.symbol if hasattr(order, 'symbol') else 'UNKNOWN',
                signal_type=SignalType.BUY if order.side == 'buy' else SignalType.SELL,
                strength=1.0,
                price=order.price if hasattr(order, 'price') else None
            )
            
            self.context.log_trade(signal, success)
        
        # 커스텀 주문 처리
        await self.on_order_execution(order)
        
        self.logger.info(f"Order filled: {order}")
    
    async def on_day_end(self) -> None:
        """일간 마감 시 호출"""
        if not self.initialized:
            return
            
        # 일일 성과 기록
        if self.context:
            account_value = self.context.get_account_value()
            position_count = len(self.current_positions)
            
            self.logger.info(
                f"Day end - Account: ${account_value:,.2f}, "
                f"Positions: {position_count}, "
                f"Signals today: {len([s for s in self.signals_history if s.timestamp.date() == self.context.current_date.date()])}"
            )
        
        # 커스텀 마감 처리
        await self.on_daily_close()
    
    def validate_parameters(self) -> bool:
        """파라미터 유효성 검사"""
        # 기본 검증
        if not self.config.parameters:
            return True
        
        # 커스텀 검증
        return self.validate_custom_parameters()
    
    def get_statistics(self) -> Dict[str, Any]:
        """전략 통계 반환"""
        return {
            "name": self.name,
            "version": self.version,
            "total_signals": self.total_signals,
            "executed_trades": self.executed_trades,
            "execution_rate": self.executed_trades / max(1, self.total_signals),
            "current_positions": len(self.current_positions),
            "data_points": len(self.data_history),
            "initialized": self.initialized
        }
    
    def _validate_signal(self, signal: Signal) -> bool:
        """신호 유효성 검사"""
        try:
            # 기본 검증
            if not signal.symbol or not signal.timestamp:
                return False
            
            if not -1.0 <= signal.strength <= 1.0:
                return False
            
            # 커스텀 검증
            return self.validate_signal(signal)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Signal validation error: {e}")
            return False
    
    def _trim_history(self, max_size: int = 1000):
        """히스토리 크기 제한"""
        if len(self.data_history) > max_size:
            self.data_history = self.data_history[-max_size:]
        
        if len(self.signals_history) > max_size:
            self.signals_history = self.signals_history[-max_size:]
    
    # 추상 메서드들 - 하위 클래스에서 구현
    @abstractmethod
    async def generate_signals(self, data: MarketData) -> List[Signal]:
        """
        신호 생성 로직 구현
        
        Args:
            data: 현재 시장 데이터
            
        Returns:
            생성된 신호 리스트
        """
        pass
    
    # 선택적 커스텀 메서드들
    async def on_initialize(self) -> None:
        """커스텀 초기화 로직"""
        pass
    
    async def on_order_execution(self, order: Any) -> None:
        """커스텀 주문 체결 처리"""
        pass
    
    async def on_daily_close(self) -> None:
        """커스텀 일일 마감 처리"""
        pass
    
    def validate_custom_parameters(self) -> bool:
        """커스텀 파라미터 검증"""
        return True
    
    def validate_signal(self, signal: Signal) -> bool:
        """커스텀 신호 검증"""
        return True


class StrategyFactory:
    """전략 팩토리"""
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy]):
        """전략 등록"""
        cls._strategies[name] = strategy_class
    
    @classmethod
    def create(cls, name: str, config: StrategyConfig) -> BaseStrategy:
        """전략 생성"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        
        strategy_class = cls._strategies[name]
        return strategy_class(config)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """등록된 전략 목록"""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_strategy_info(cls, name: str) -> Dict[str, Any]:
        """전략 정보 조회"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        
        strategy_class = cls._strategies[name]
        
        # 임시 설정으로 인스턴스 생성하여 정보 추출
        temp_config = StrategyConfig(name=name)
        temp_instance = strategy_class(temp_config)
        
        return {
            "name": name,
            "class_name": strategy_class.__name__,
            "module": strategy_class.__module__,
            "doc": strategy_class.__doc__ or "",
            "parameters": getattr(temp_instance, 'parameter_definitions', {}),
        }