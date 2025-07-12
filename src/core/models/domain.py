"""
도메인 모델 정의
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class TransactionType(Enum):
    """거래 유형"""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    FEE = "fee"


class AccountType(Enum):
    """계좌 유형"""
    STOCK = "stock"
    FUTURES = "futures"
    OPTIONS = "options"
    FOREX = "forex"


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: int
    average_price: float
    
    # 추가 정보
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    realized_pnl: float = 0.0
    
    @property
    def cost_basis(self) -> float:
        """총 매입금액"""
        return self.quantity * self.average_price
    
    def add_quantity(self, quantity: int, price: float) -> None:
        """포지션 추가 (매수)"""
        total_cost = self.cost_basis + (quantity * price)
        self.quantity += quantity
        self.average_price = total_cost / self.quantity
        self.updated_at = datetime.now()
    
    def reduce_quantity(self, quantity: int, price: float) -> float:
        """포지션 감소 (매도)"""
        if quantity > self.quantity:
            raise ValueError("Cannot reduce more than current quantity")
        
        # 실현 손익 계산
        realized_pnl = quantity * (price - self.average_price)
        self.realized_pnl += realized_pnl
        
        # 수량 감소
        self.quantity -= quantity
        self.updated_at = datetime.now()
        
        return realized_pnl
    
    def calculate_pnl(self, current_price: float) -> Dict[str, float]:
        """손익 계산"""
        market_value = self.quantity * current_price
        unrealized_pnl = market_value - self.cost_basis
        unrealized_pnl_percent = (unrealized_pnl / self.cost_basis) * 100 if self.cost_basis > 0 else 0
        
        return {
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": unrealized_pnl_percent,
            "realized_pnl": self.realized_pnl,
            "total_pnl": unrealized_pnl + self.realized_pnl
        }


@dataclass
class Transaction:
    """거래 내역"""
    symbol: str
    transaction_type: TransactionType
    quantity: int
    price: float
    commission: float = 0.0
    tax: float = 0.0
    
    # 시간 정보
    executed_at: datetime = field(default_factory=datetime.now)
    
    # 추가 정보
    order_id: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def amount(self) -> float:
        """거래 금액 (수수료/세금 제외)"""
        return self.quantity * self.price
    
    @property
    def net_amount(self) -> float:
        """순 거래 금액 (수수료/세금 포함)"""
        if self.transaction_type == TransactionType.BUY:
            return self.amount + self.commission + self.tax
        else:  # SELL
            return self.amount - self.commission - self.tax


@dataclass
class Portfolio:
    """포트폴리오"""
    account_id: str
    initial_capital: float
    
    # 상태
    cash: float = None
    positions: Dict[str, Position] = field(default_factory=dict)
    transactions: List[Transaction] = field(default_factory=list)
    
    # 시간 정보
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.cash is None:
            self.cash = self.initial_capital
    
    @property
    def total_value(self) -> float:
        """포트폴리오 총 가치 (현재가 기준)"""
        # 현재가 정보가 없으므로 현금만 반환
        # 실제 구현에서는 current_prices를 받아서 계산
        return self.cash
    
    def add_position(self, symbol: str, quantity: int, price: float, commission: float = 0.0) -> Position:
        """포지션 추가/업데이트"""
        # 거래 비용
        total_cost = (quantity * price) + commission
        
        if self.cash < total_cost:
            raise ValueError("Insufficient cash")
        
        # 현금 차감
        self.cash -= total_cost
        
        # 포지션 업데이트
        if symbol in self.positions:
            self.positions[symbol].add_quantity(quantity, price)
        else:
            self.positions[symbol] = Position(symbol, quantity, price)
        
        # 거래 기록
        transaction = Transaction(
            symbol=symbol,
            transaction_type=TransactionType.BUY,
            quantity=quantity,
            price=price,
            commission=commission
        )
        self.transactions.append(transaction)
        
        self.updated_at = datetime.now()
        return self.positions[symbol]
    
    def close_position(self, symbol: str, price: float, commission: float = 0.0, tax: float = 0.0) -> float:
        """포지션 전량 청산"""
        if symbol not in self.positions:
            raise ValueError(f"Position {symbol} not found")
        
        position = self.positions[symbol]
        quantity = position.quantity
        
        # 실현 손익
        realized_pnl = position.reduce_quantity(quantity, price)
        
        # 순 수익 (수수료/세금 차감)
        net_proceeds = (quantity * price) - commission - tax
        net_pnl = realized_pnl - commission - tax
        
        # 현금 증가
        self.cash += net_proceeds
        
        # 포지션 제거
        del self.positions[symbol]
        
        # 거래 기록
        transaction = Transaction(
            symbol=symbol,
            transaction_type=TransactionType.SELL,
            quantity=quantity,
            price=price,
            commission=commission,
            tax=tax
        )
        self.transactions.append(transaction)
        
        self.updated_at = datetime.now()
        return net_pnl
    
    def calculate_value(self, current_prices: Dict[str, float]) -> Dict[str, any]:
        """포트폴리오 평가"""
        position_values = {}
        total_market_value = 0
        total_unrealized_pnl = 0
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                pnl_info = position.calculate_pnl(current_price)
                
                position_values[symbol] = pnl_info
                total_market_value += pnl_info["market_value"]
                total_unrealized_pnl += pnl_info["unrealized_pnl"]
        
        total_value = self.cash + total_market_value
        total_pnl = total_unrealized_pnl
        
        return {
            "total_value": total_value,
            "cash": self.cash,
            "market_value": total_market_value,
            "total_pnl": total_pnl,
            "total_pnl_percent": (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
            "positions": position_values
        }


@dataclass
class Account:
    """계좌 정보"""
    account_id: str
    account_type: AccountType
    name: str
    currency: str = "KRW"
    
    # 상태
    is_active: bool = True
    is_tradeable: bool = True
    
    # 제한
    max_order_amount: Optional[float] = None
    max_position_size: Optional[float] = None
    
    # 시간 정보
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)