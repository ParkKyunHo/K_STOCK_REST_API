"""
주문 관리자 인터페이스 테스트
"""
import pytest
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class MockOrder:
    """테스트용 주문 객체"""
    def __init__(self, order_id: str, symbol: str, side: OrderSide, 
                 quantity: int, order_type: OrderType, price: Optional[float] = None):
        self.id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.average_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class MockOrderManager:
    """IOrderManager 테스트를 위한 Mock 구현체"""
    
    def __init__(self):
        self.orders: Dict[str, MockOrder] = {}
        self.order_counter = 0
        self.connected = False
    
    async def connect(self, account_info: Dict[str, str]) -> bool:
        self.account_info = account_info
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        self.connected = False
    
    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> MockOrder:
        # 주문 ID 생성
        self.order_counter += 1
        order_id = f"ORD{self.order_counter:06d}"
        
        # 주문 생성
        order = MockOrder(order_id, symbol, side, quantity, order_type, price)
        order.status = OrderStatus.SUBMITTED
        
        # 주문 저장
        self.orders[order_id] = order
        
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                return True
        return False
    
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None
    ) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                if quantity is not None:
                    order.quantity = quantity
                if price is not None:
                    order.price = price
                order.updated_at = datetime.now()
                return True
        return False
    
    async def get_order(self, order_id: str) -> Optional[MockOrder]:
        return self.orders.get(order_id)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[MockOrder]:
        open_statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        orders = [
            order for order in self.orders.values()
            if order.status in open_statuses
        ]
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        return orders
    
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MockOrder]:
        orders = list(self.orders.values())
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        if start_date:
            orders = [order for order in orders if order.created_at >= start_date]
        
        if end_date:
            orders = [order for order in orders if order.created_at <= end_date]
        
        return orders


class TestIOrderManagerInterface:
    """IOrderManager 인터페이스 테스트"""
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """연결 생명주기 테스트"""
        manager = MockOrderManager()
        
        assert not manager.connected
        
        # 연결
        account_info = {"account_no": "12345678", "account_type": "stock"}
        result = await manager.connect(account_info)
        assert result is True
        assert manager.connected
        
        # 연결 해제
        await manager.disconnect()
        assert not manager.connected
    
    @pytest.mark.asyncio
    async def test_order_submission(self):
        """주문 제출 테스트"""
        manager = MockOrderManager()
        await manager.connect({"account_no": "12345678"})
        
        # 시장가 매수 주문
        order = await manager.submit_order(
            symbol="005930",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        assert order is not None
        assert order.symbol == "005930"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.SUBMITTED
        
        # 지정가 매도 주문
        order2 = await manager.submit_order(
            symbol="000660",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=150000
        )
        
        assert order2.price == 150000
        assert order2.order_type == OrderType.LIMIT
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self):
        """주문 취소 테스트"""
        manager = MockOrderManager()
        await manager.connect({"account_no": "12345678"})
        
        # 주문 생성
        order = await manager.submit_order(
            symbol="005930",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=70000
        )
        
        # 주문 취소
        result = await manager.cancel_order(order.id)
        assert result is True
        
        # 취소된 주문 확인
        cancelled_order = await manager.get_order(order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED
        
        # 이미 취소된 주문 재취소 시도
        result = await manager.cancel_order(order.id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_order_modification(self):
        """주문 수정 테스트"""
        manager = MockOrderManager()
        await manager.connect({"account_no": "12345678"})
        
        # 주문 생성
        order = await manager.submit_order(
            symbol="005930",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=70000
        )
        
        # 수량 및 가격 수정
        result = await manager.modify_order(
            order.id,
            quantity=150,
            price=69000
        )
        assert result is True
        
        # 수정 확인
        modified_order = await manager.get_order(order.id)
        assert modified_order.quantity == 150
        assert modified_order.price == 69000
    
    @pytest.mark.asyncio
    async def test_open_orders_retrieval(self):
        """미체결 주문 조회 테스트"""
        manager = MockOrderManager()
        await manager.connect({"account_no": "12345678"})
        
        # 여러 주문 생성
        await manager.submit_order("005930", OrderSide.BUY, 100, OrderType.LIMIT, 70000)
        await manager.submit_order("000660", OrderSide.SELL, 50, OrderType.LIMIT, 150000)
        order3 = await manager.submit_order("005930", OrderSide.BUY, 200, OrderType.LIMIT, 69000)
        
        # 하나 취소
        await manager.cancel_order(order3.id)
        
        # 전체 미체결 주문 조회
        open_orders = await manager.get_open_orders()
        assert len(open_orders) == 2
        
        # 종목별 미체결 주문 조회
        samsung_orders = await manager.get_open_orders("005930")
        assert len(samsung_orders) == 1
    
    @pytest.mark.asyncio
    async def test_order_history(self):
        """주문 이력 조회 테스트"""
        manager = MockOrderManager()
        await manager.connect({"account_no": "12345678"})
        
        # 주문 생성
        await manager.submit_order("005930", OrderSide.BUY, 100, OrderType.MARKET)
        await manager.submit_order("000660", OrderSide.SELL, 50, OrderType.LIMIT, 150000)
        
        # 전체 이력 조회
        history = await manager.get_order_history()
        assert len(history) == 2
        
        # 종목별 이력 조회
        samsung_history = await manager.get_order_history(symbol="005930")
        assert len(samsung_history) == 1
        assert samsung_history[0].symbol == "005930"