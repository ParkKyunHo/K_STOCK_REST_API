"""
주문 관리자 인터페이스
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """주문 방향"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TimeInForce(Enum):
    """주문 유효 기간"""
    DAY = "day"  # 당일
    GTC = "gtc"  # Good Till Cancel
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class Order:
    """주문 정보"""
    id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    status: OrderStatus
    
    # 가격 정보
    price: Optional[float] = None
    stop_price: Optional[float] = None
    average_price: float = 0.0
    
    # 체결 정보
    filled_quantity: int = 0
    remaining_quantity: int = 0
    
    # 시간 정보
    created_at: datetime = None
    updated_at: datetime = None
    filled_at: Optional[datetime] = None
    
    # 추가 정보
    time_in_force: TimeInForce = TimeInForce.DAY
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.remaining_quantity == 0:
            self.remaining_quantity = self.quantity
        if self.metadata is None:
            self.metadata = {}


class IOrderManager(ABC):
    """주문 관리자 인터페이스"""
    
    @abstractmethod
    async def connect(self, account_info: Dict[str, str]) -> bool:
        """
        계좌 연결
        
        Args:
            account_info: 계좌 정보 (account_no, account_type 등)
            
        Returns:
            연결 성공 여부
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """계좌 연결 해제"""
        pass
    
    @abstractmethod
    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Order:
        """
        주문 제출
        
        Args:
            symbol: 종목 코드
            side: 매수/매도
            quantity: 수량
            order_type: 주문 타입
            price: 지정가 (LIMIT, STOP_LIMIT 주문 시)
            stop_price: 스톱 가격 (STOP, STOP_LIMIT 주문 시)
            time_in_force: 주문 유효 기간
            
        Returns:
            제출된 주문 정보
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소
        
        Args:
            order_id: 주문 ID
            
        Returns:
            취소 성공 여부
        """
        pass
    
    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None
    ) -> bool:
        """
        주문 수정
        
        Args:
            order_id: 주문 ID
            quantity: 변경할 수량
            price: 변경할 가격
            
        Returns:
            수정 성공 여부
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        주문 정보 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            주문 정보 또는 None
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        미체결 주문 조회
        
        Args:
            symbol: 종목 코드 (None이면 전체)
            
        Returns:
            미체결 주문 리스트
        """
        pass
    
    @abstractmethod
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Order]:
        """
        주문 이력 조회
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            주문 이력 리스트
        """
        pass