# -*- coding: utf-8 -*-
"""
백테스트 모델
"""
import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.models.domain import Portfolio, Transaction


class BacktestStatus(enum.Enum):
    """백테스트 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    commission_rate: Decimal = Decimal("0.0015")  # 0.15% 기본 수수료
    tax_rate: Decimal = Decimal("0.003")         # 0.3% 기본 세금
    slippage_rate: Decimal = Decimal("0.001")    # 0.1% 기본 슬리피지
    
    def __post_init__(self):
        """설정 검증"""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        
        if self.commission_rate < 0:
            raise ValueError("commission_rate must be non-negative")
        
        if self.tax_rate < 0:
            raise ValueError("tax_rate must be non-negative")
        
        if self.slippage_rate < 0:
            raise ValueError("slippage_rate must be non-negative")
    
    @property
    def duration_days(self) -> int:
        """백테스트 기간 (일수)"""
        return (self.end_date - self.start_date).days


@dataclass
class BacktestResult:
    """백테스트 결과"""
    config: BacktestConfig
    status: BacktestStatus
    start_time: datetime
    end_time: datetime
    final_portfolio: Portfolio
    transactions: List[Transaction]
    daily_returns: List[Decimal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def execution_time_seconds(self) -> float:
        """실행 시간 (초)"""
        return (self.end_time - self.start_time).total_seconds()
    
    def calculate_total_value(self) -> Decimal:
        """총 포트폴리오 가치 계산"""
        # 현금 잔고
        total_value = Decimal(str(self.final_portfolio.cash))
        
        # 포지션 가치 합산 (현재가 정보가 없으므로 평균가 사용)
        for symbol, position in self.final_portfolio.positions.items():
            position_value = Decimal(str(position.average_price)) * Decimal(str(position.quantity))
            total_value += position_value
        
        return total_value
    
    def calculate_total_return(self) -> Decimal:
        """총 수익률 계산"""
        total_value = self.calculate_total_value()
        initial_capital = self.config.initial_capital
        
        if initial_capital == 0:
            return Decimal("0")
        
        return (total_value - initial_capital) / initial_capital
    
    def calculate_absolute_profit(self) -> Decimal:
        """절대 수익 계산"""
        total_value = self.calculate_total_value()
        return total_value - self.config.initial_capital
    
    def is_successful(self) -> bool:
        """백테스트 성공 여부"""
        return self.status == BacktestStatus.COMPLETED
    
    def get_transaction_count(self) -> int:
        """거래 횟수"""
        return len(self.transactions)
    
    def get_buy_count(self) -> int:
        """매수 거래 횟수"""
        return len([t for t in self.transactions if t.transaction_type.upper() == "BUY"])
    
    def get_sell_count(self) -> int:
        """매도 거래 횟수"""
        return len([t for t in self.transactions if t.transaction_type.upper() == "SELL"])
    
    def get_total_commission(self) -> Decimal:
        """총 수수료"""
        return sum(t.commission or Decimal("0") for t in self.transactions)
    
    def get_trading_period_days(self) -> int:
        """실제 거래 기간 (일수)"""
        if not self.transactions:
            return 0
        
        first_trade = min(t.timestamp for t in self.transactions)
        last_trade = max(t.timestamp for t in self.transactions)
        return (last_trade - first_trade).days + 1