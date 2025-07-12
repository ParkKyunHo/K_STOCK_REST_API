"""
핵심 인터페이스 테스트
"""
import pytest
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

# 테스트를 위한 Mock 구현체들을 먼저 정의


class MockStrategy:
    """IStrategy 테스트를 위한 Mock 구현체"""
    
    def __init__(self, name: str = "MockStrategy"):
        self._name = name
        self._version = "1.0.0"
        self._description = "Mock strategy for testing"
        self._parameters = {"param1": 10, "param2": 20}
        self.initialized = False
        self.data_received = []
        self.orders_filled = []
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters
    
    async def initialize(self, context: Any) -> None:
        self.initialized = True
        self.context = context
    
    async def on_data(self, data: Any) -> List[Any]:
        self.data_received.append(data)
        # 간단한 신호 생성 로직
        if len(self.data_received) > 5:
            return [{"type": "BUY", "symbol": "005930", "quantity": 100}]
        return []
    
    async def on_order_filled(self, order: Any) -> None:
        self.orders_filled.append(order)
    
    async def on_day_end(self) -> None:
        pass
    
    def validate_parameters(self) -> bool:
        return all(key in self._parameters for key in ["param1", "param2"])


class TestIStrategyInterface:
    """IStrategy 인터페이스 테스트"""
    
    def test_strategy_properties(self):
        """전략 속성 테스트"""
        strategy = MockStrategy("TestStrategy")
        
        assert strategy.name == "TestStrategy"
        assert strategy.version == "1.0.0"
        assert strategy.description == "Mock strategy for testing"
        assert isinstance(strategy.parameters, dict)
        assert "param1" in strategy.parameters
    
    @pytest.mark.asyncio
    async def test_strategy_initialization(self):
        """전략 초기화 테스트"""
        strategy = MockStrategy()
        context = {"portfolio": "mock_portfolio", "logger": "mock_logger"}
        
        assert not strategy.initialized
        
        await strategy.initialize(context)
        
        assert strategy.initialized
        assert strategy.context == context
    
    @pytest.mark.asyncio
    async def test_strategy_on_data(self):
        """데이터 수신 처리 테스트"""
        strategy = MockStrategy()
        
        # 처음 몇 개의 데이터는 신호 생성 안함
        for i in range(5):
            signals = await strategy.on_data({"price": 100 + i})
            assert signals == []
        
        # 6번째 데이터에서 신호 생성
        signals = await strategy.on_data({"price": 105})
        assert len(signals) == 1
        assert signals[0]["type"] == "BUY"
    
    @pytest.mark.asyncio
    async def test_strategy_order_handling(self):
        """주문 처리 테스트"""
        strategy = MockStrategy()
        order = {"id": "123", "symbol": "005930", "status": "filled"}
        
        assert len(strategy.orders_filled) == 0
        
        await strategy.on_order_filled(order)
        
        assert len(strategy.orders_filled) == 1
        assert strategy.orders_filled[0] == order
    
    def test_parameter_validation(self):
        """파라미터 검증 테스트"""
        strategy = MockStrategy()
        assert strategy.validate_parameters() is True
        
        # 잘못된 파라미터로 테스트
        strategy._parameters = {"wrong_param": 10}
        assert strategy.validate_parameters() is False


class TestStrategyInterfaceContract:
    """IStrategy 인터페이스 계약 테스트"""
    
    def test_required_properties(self):
        """필수 속성 존재 확인"""
        strategy = MockStrategy()
        
        # 모든 필수 속성이 있는지 확인
        required_properties = ["name", "version", "description", "parameters"]
        for prop in required_properties:
            assert hasattr(strategy, prop)
    
    def test_required_methods(self):
        """필수 메서드 존재 확인"""
        strategy = MockStrategy()
        
        # 모든 필수 메서드가 있는지 확인
        required_methods = [
            "initialize", "on_data", "on_order_filled", 
            "on_day_end", "validate_parameters"
        ]
        for method in required_methods:
            assert hasattr(strategy, method)
            assert callable(getattr(strategy, method))


class MockMarketDataProvider:
    """IMarketDataProvider 테스트를 위한 Mock 구현체"""
    
    def __init__(self):
        self.connected = False
        self.subscriptions = {}
        self.mock_data = {}
    
    async def connect(self) -> bool:
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        self.connected = False
        self.subscriptions.clear()
    
    async def subscribe(self, symbols: List[str], data_type: str = "quote") -> bool:
        for symbol in symbols:
            self.subscriptions[symbol] = data_type
        return True
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        for symbol in symbols:
            self.subscriptions.pop(symbol, None)
        return True
    
    async def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        if symbol in self.mock_data:
            return self.mock_data[symbol]
        return None
    
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        # Mock 데이터 생성
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [101 + i for i in range(len(dates))],
            'low': [99 + i for i in range(len(dates))],
            'close': [100.5 + i for i in range(len(dates))],
            'volume': [1000000 + i * 1000 for i in range(len(dates))]
        }, index=dates)
        return data
    
    def is_connected(self) -> bool:
        return self.connected


class TestIMarketDataProviderInterface:
    """IMarketDataProvider 인터페이스 테스트"""
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """연결 생명주기 테스트"""
        provider = MockMarketDataProvider()
        
        assert not provider.is_connected()
        
        # 연결
        result = await provider.connect()
        assert result is True
        assert provider.is_connected()
        
        # 연결 해제
        await provider.disconnect()
        assert not provider.is_connected()
    
    @pytest.mark.asyncio
    async def test_subscription_management(self):
        """구독 관리 테스트"""
        provider = MockMarketDataProvider()
        await provider.connect()
        
        # 구독
        symbols = ["005930", "000660"]
        result = await provider.subscribe(symbols, "quote")
        assert result is True
        assert len(provider.subscriptions) == 2
        
        # 구독 해제
        result = await provider.unsubscribe(["005930"])
        assert result is True
        assert len(provider.subscriptions) == 1
        assert "000660" in provider.subscriptions
    
    @pytest.mark.asyncio
    async def test_latest_data_retrieval(self):
        """최신 데이터 조회 테스트"""
        provider = MockMarketDataProvider()
        await provider.connect()
        
        # Mock 데이터 설정
        provider.mock_data["005930"] = {
            "symbol": "005930",
            "price": 70000,
            "volume": 1000000
        }
        
        # 데이터 조회
        data = await provider.get_latest_data("005930")
        assert data is not None
        assert data["price"] == 70000
        
        # 없는 종목 조회
        data = await provider.get_latest_data("999999")
        assert data is None
    
    @pytest.mark.asyncio
    async def test_historical_data_retrieval(self):
        """과거 데이터 조회 테스트"""
        provider = MockMarketDataProvider()
        await provider.connect()
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        data = await provider.get_historical_data(
            "005930", start_date, end_date, "1d"
        )
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 10
        assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume'])