"""
전략 인터페이스 정의
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class SignalType(Enum):
    """신호 타입"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"
    CLOSE_ALL = "close_all"


@dataclass
class Signal:
    """거래 신호"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    strength: float  # -1.0 ~ 1.0
    quantity: Optional[int] = None
    price: Optional[float] = None
    reason: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # 신호 강도 검증
        if not -1.0 <= self.strength <= 1.0:
            raise ValueError("Signal strength must be between -1.0 and 1.0")


@dataclass
class MarketData:
    """시장 데이터"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    # 추가 정보
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class IStrategy(ABC):
    """전략 기본 인터페이스"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """전략 버전"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """전략 설명"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """전략 파라미터"""
        pass
    
    @abstractmethod
    async def initialize(self, context: Any) -> None:
        """
        전략 초기화
        
        Args:
            context: 전략 실행 컨텍스트 (StrategyContext)
        """
        pass
    
    @abstractmethod
    async def on_data(self, data: MarketData) -> List[Signal]:
        """
        데이터 수신 시 호출
        
        Args:
            data: 시장 데이터
            
        Returns:
            생성된 신호 리스트
        """
        pass
    
    @abstractmethod
    async def on_order_filled(self, order: Any) -> None:
        """
        주문 체결 시 호출
        
        Args:
            order: 체결된 주문 정보
        """
        pass
    
    @abstractmethod
    async def on_day_end(self) -> None:
        """일간 마감 시 호출"""
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """파라미터 유효성 검사"""
        pass