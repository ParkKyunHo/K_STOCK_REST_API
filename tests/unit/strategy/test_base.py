# -*- coding: utf-8 -*-
"""
BaseStrategy 테스트
"""
import asyncio
import logging
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from src.strategy.base import (
    BaseStrategy, StrategyConfig, StrategyContext, StrategyFactory
)
from src.core.interfaces.strategy import Signal, SignalType, MarketData
from src.core.models.domain import Portfolio
from src.core.interfaces import IMarketDataProvider


# 테스트용 구체 전략 클래스
class TestStrategy(BaseStrategy):
    """테스트용 전략"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.signals_generated = []
    
    async def generate_signals(self, data: MarketData):
        """테스트용 신호 생성"""
        # 단순히 가격이 100 이상이면 매수 신호
        if data.close >= 100:
            signal = Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=0.8,
                price=data.close,
                reason="Test buy signal"
            )
            self.signals_generated.append(signal)
            return [signal]
        return []


class TestStrategyConfig:
    """StrategyConfig 테스트"""
    
    def test_strategy_config_creation(self):
        """전략 설정 생성 테스트"""
        config = StrategyConfig(
            name="Test Strategy",
            version="1.0.0",
            description="Test strategy description",
            parameters={"param1": 10, "param2": "value"},
            tags=["test", "sample"],
            author="Test Author"
        )
        
        assert config.name == "Test Strategy"
        assert config.version == "1.0.0"
        assert config.description == "Test strategy description"
        assert config.parameters == {"param1": 10, "param2": "value"}
        assert config.tags == ["test", "sample"]
        assert config.author == "Test Author"
        assert isinstance(config.created_at, datetime)
    
    def test_strategy_config_defaults(self):
        """전략 설정 기본값 테스트"""
        config = StrategyConfig(name="Minimal Strategy")
        
        assert config.name == "Minimal Strategy"
        assert config.version == "1.0.0"
        assert config.description == ""
        assert config.parameters == {}
        assert config.tags == []
        assert config.author == ""
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        config = StrategyConfig(
            name="Test Strategy",
            parameters={"key": "value"}
        )
        
        result = config.to_dict()
        
        assert result["name"] == "Test Strategy"
        assert result["parameters"] == {"key": "value"}
        assert "created_at" in result
        assert isinstance(result["created_at"], str)


class TestStrategyContext:
    """StrategyContext 테스트"""
    
    @pytest.fixture
    def mock_portfolio(self):
        """Mock 포트폴리오"""
        portfolio = Mock(spec=Portfolio)
        portfolio.total_value = 10000000.0
        portfolio.cash = 5000000.0
        portfolio.positions = {}
        return portfolio
    
    @pytest.fixture
    def mock_data_provider(self):
        """Mock 데이터 제공자"""
        provider = Mock(spec=IMarketDataProvider)
        return provider
    
    @pytest.fixture
    def strategy_context(self, mock_portfolio, mock_data_provider):
        """전략 컨텍스트"""
        return StrategyContext(
            portfolio=mock_portfolio,
            data_provider=mock_data_provider,
            logger=logging.getLogger("test"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=Decimal("10000000")
        )
    
    def test_context_creation(self, strategy_context):
        """컨텍스트 생성 테스트"""
        assert strategy_context.initial_capital == Decimal("10000000")
        assert strategy_context.commission_rate == Decimal("0.00015")
        assert strategy_context.slippage_rate == Decimal("0.0001")
        assert strategy_context.is_live is False
        assert strategy_context.trade_count == 0
    
    def test_get_current_positions(self, strategy_context):
        """현재 포지션 조회 테스트"""
        positions = strategy_context.get_current_positions()
        assert positions == {}
    
    def test_get_account_value(self, strategy_context):
        """계좌 가치 조회 테스트"""
        # get_account_value는 portfolio.get_total_value()를 호출하므로 Mock을 수정
        strategy_context.portfolio.get_total_value = Mock(return_value=10000000.0)
        value = strategy_context.get_account_value()
        assert value == 10000000.0
    
    def test_get_cash_balance(self, strategy_context):
        """현금 잔고 조회 테스트"""
        balance = strategy_context.get_cash_balance()
        assert balance == 5000000.0
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, strategy_context):
        """과거 데이터 조회 테스트"""
        import pandas as pd
        
        # Mock 데이터 설정
        mock_data = [{"date": datetime.now(), "close": 100.0}]
        strategy_context.data_provider.get_ohlcv = AsyncMock(return_value=mock_data)
        
        result = await strategy_context.get_historical_data("TEST", 10)
        
        assert isinstance(result, pd.DataFrame)
        strategy_context.data_provider.get_ohlcv.assert_called_once()
    
    def test_log_trade(self, strategy_context):
        """거래 로그 테스트"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="TEST",
            signal_type=SignalType.BUY,
            strength=1.0,
            price=100.0
        )
        
        strategy_context.log_trade(signal, success=True)
        
        assert strategy_context.trade_count == 1
        assert strategy_context.winning_trades == 1
        assert strategy_context.losing_trades == 0


class TestBaseStrategy:
    """BaseStrategy 테스트"""
    
    @pytest.fixture
    def strategy_config(self):
        """전략 설정"""
        return StrategyConfig(
            name="Test Strategy",
            parameters={"test_param": 100}
        )
    
    @pytest.fixture
    def test_strategy(self, strategy_config):
        """테스트 전략"""
        return TestStrategy(strategy_config)
    
    @pytest.fixture
    def strategy_context(self):
        """전략 컨텍스트"""
        portfolio = Mock(spec=Portfolio)
        portfolio.get_total_value = Mock(return_value=10000000.0)
        portfolio.cash = 5000000.0
        portfolio.positions = {}
        
        return StrategyContext(
            portfolio=portfolio,
            data_provider=Mock(spec=IMarketDataProvider),
            logger=logging.getLogger("test"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=Decimal("10000000")
        )
    
    def test_strategy_properties(self, test_strategy):
        """전략 속성 테스트"""
        assert test_strategy.name == "Test Strategy"
        assert test_strategy.version == "1.0.0"
        assert test_strategy.description == ""
        assert test_strategy.parameters == {"test_param": 100}
    
    @pytest.mark.asyncio
    async def test_strategy_initialization(self, test_strategy, strategy_context):
        """전략 초기화 테스트"""
        assert test_strategy.initialized is False
        
        await test_strategy.initialize(strategy_context)
        
        assert test_strategy.initialized is True
        assert test_strategy.context == strategy_context
        assert test_strategy.logger is not None
    
    @pytest.mark.asyncio
    async def test_strategy_initialization_with_invalid_params(self, strategy_context):
        """잘못된 파라미터로 초기화 테스트"""
        # validate_custom_parameters가 False를 반환하는 전략
        class InvalidParamStrategy(TestStrategy):
            def validate_custom_parameters(self):
                return False
        
        # 파라미터가 있어야 validate_custom_parameters가 호출됨
        config = StrategyConfig(name="Invalid Strategy", parameters={"invalid": True})
        strategy = InvalidParamStrategy(config)
        
        with pytest.raises(ValueError, match="Invalid parameters for strategy"):
            await strategy.initialize(strategy_context)
    
    @pytest.mark.asyncio
    async def test_on_data_processing(self, test_strategy, strategy_context):
        """데이터 처리 테스트"""
        await test_strategy.initialize(strategy_context)
        
        # 매수 신호를 생성할 데이터
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now(),
            open=99.0,
            high=101.0,
            low=98.0,
            close=100.0,
            volume=1000000
        )
        
        signals = await test_strategy.on_data(data)
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].symbol == "TEST"
        assert len(test_strategy.data_history) == 1
        assert len(test_strategy.signals_history) == 1
    
    @pytest.mark.asyncio
    async def test_on_data_without_initialization(self, test_strategy):
        """초기화 없이 데이터 처리 테스트"""
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now(),
            open=99.0,
            high=101.0,
            low=98.0,
            close=100.0,
            volume=1000000
        )
        
        with pytest.raises(RuntimeError):
            await test_strategy.on_data(data)
    
    @pytest.mark.asyncio
    async def test_on_order_filled(self, test_strategy, strategy_context):
        """주문 체결 처리 테스트"""
        await test_strategy.initialize(strategy_context)
        
        # Mock 주문
        order = Mock()
        order.symbol = "TEST"
        order.side = "buy"
        order.price = 100.0
        order.status = "filled"
        
        # 체결 처리 (예외 발생하지 않아야 함)
        await test_strategy.on_order_filled(order)
        
        assert test_strategy.executed_trades == 1
    
    @pytest.mark.asyncio
    async def test_on_day_end(self, test_strategy, strategy_context):
        """일간 마감 테스트"""
        await test_strategy.initialize(strategy_context)
        
        # 마감 처리 (예외 발생하지 않아야 함)
        await test_strategy.on_day_end()
    
    def test_validate_parameters_default(self, test_strategy):
        """기본 파라미터 검증 테스트"""
        result = test_strategy.validate_parameters()
        assert result is True
    
    def test_get_statistics(self, test_strategy):
        """전략 통계 테스트"""
        stats = test_strategy.get_statistics()
        
        assert stats["name"] == "Test Strategy"
        assert stats["version"] == "1.0.0"
        assert stats["total_signals"] == 0
        assert stats["executed_trades"] == 0
        assert stats["initialized"] is False
    
    @pytest.mark.asyncio
    async def test_signal_validation(self, test_strategy, strategy_context):
        """신호 검증 테스트"""
        await test_strategy.initialize(strategy_context)
        
        # Signal 생성 시 유효성 검사가 이미 되므로 잘못된 신호는 생성할 수 없음
        # 대신 올바른 신호로 검증 로직 테스트
        with pytest.raises(ValueError):
            Signal(
                timestamp=datetime.now(),
                symbol="TEST",
                signal_type=SignalType.BUY,
                strength=2.0,  # 1.0 초과 - ValueError 발생
                price=100.0
            )
        
        # 올바른 신호는 생성되어야 함
        valid_signal = Signal(
            timestamp=datetime.now(),
            symbol="TEST",
            signal_type=SignalType.BUY,
            strength=0.8,  # 유효한 범위
            price=100.0
        )
        
        # 유효한 신호는 _validate_signal을 통과해야 함
        assert test_strategy._validate_signal(valid_signal) is True
    
    def test_history_trimming(self, test_strategy, strategy_context):
        """히스토리 크기 제한 테스트"""
        # 이것은 private 메서드 테스트이므로, 
        # 많은 데이터를 넣어서 트림이 일어나는지 확인
        test_strategy.data_history = [Mock() for _ in range(1500)]
        test_strategy.signals_history = [Mock() for _ in range(1500)]
        
        test_strategy._trim_history(max_size=1000)
        
        assert len(test_strategy.data_history) == 1000
        assert len(test_strategy.signals_history) == 1000


class TestStrategyFactory:
    """StrategyFactory 테스트"""
    
    def test_register_strategy(self):
        """전략 등록 테스트"""
        # 기존 등록된 전략 수
        initial_count = len(StrategyFactory.list_strategies())
        
        # 새 전략 등록
        StrategyFactory.register("test_strategy", TestStrategy)
        
        # 등록 확인
        strategies = StrategyFactory.list_strategies()
        assert "test_strategy" in strategies
        assert len(strategies) == initial_count + 1
    
    def test_create_strategy(self):
        """전략 생성 테스트"""
        # 전략 등록
        StrategyFactory.register("test_strategy", TestStrategy)
        
        # 전략 생성
        config = StrategyConfig(name="Test Strategy")
        strategy = StrategyFactory.create("test_strategy", config)
        
        assert isinstance(strategy, TestStrategy)
        assert strategy.name == "Test Strategy"
    
    def test_create_unknown_strategy(self):
        """알 수 없는 전략 생성 테스트"""
        config = StrategyConfig(name="Unknown Strategy")
        
        with pytest.raises(ValueError):
            StrategyFactory.create("unknown_strategy", config)
    
    def test_get_strategy_info(self):
        """전략 정보 조회 테스트"""
        # 전략 등록
        StrategyFactory.register("test_strategy", TestStrategy)
        
        # 정보 조회
        info = StrategyFactory.get_strategy_info("test_strategy")
        
        assert info["name"] == "test_strategy"
        assert info["class_name"] == "TestStrategy"
        assert "module" in info
    
    def test_get_unknown_strategy_info(self):
        """알 수 없는 전략 정보 조회 테스트"""
        with pytest.raises(ValueError):
            StrategyFactory.get_strategy_info("unknown_strategy")


# 통합 테스트
class TestStrategyIntegration:
    """전략 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_strategy_lifecycle(self):
        """전략 전체 생명주기 테스트"""
        # 1. 전략 설정 및 생성
        config = StrategyConfig(
            name="Integration Test Strategy",
            parameters={"threshold": 100}
        )
        strategy = TestStrategy(config)
        
        # 2. 컨텍스트 생성
        portfolio = Mock(spec=Portfolio)
        portfolio.get_total_value = Mock(return_value=10000000.0)
        portfolio.cash = 5000000.0
        portfolio.positions = {}
        
        context = StrategyContext(
            portfolio=portfolio,
            data_provider=Mock(spec=IMarketDataProvider),
            logger=logging.getLogger("integration_test"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=Decimal("10000000")
        )
        
        # 3. 전략 초기화
        await strategy.initialize(context)
        assert strategy.initialized is True
        
        # 4. 데이터 처리 및 신호 생성
        data_points = [
            MarketData("TEST", datetime.now(), 90, 95, 85, 90, 1000000),   # 신호 없음
            MarketData("TEST", datetime.now(), 100, 105, 95, 100, 1000000), # 매수 신호
            MarketData("TEST", datetime.now(), 105, 110, 100, 105, 1000000), # 매수 신호
        ]
        
        total_signals = 0
        for data in data_points:
            signals = await strategy.on_data(data)
            total_signals += len(signals)
        
        assert total_signals == 2  # 100 이상인 데이터 2개
        assert len(strategy.data_history) == 3
        assert len(strategy.signals_history) == 2
        
        # 5. 주문 체결 처리
        order = Mock()
        order.symbol = "TEST"
        order.side = "buy"
        order.price = 100.0
        order.status = "filled"
        
        await strategy.on_order_filled(order)
        assert strategy.executed_trades == 1
        
        # 6. 일간 마감
        await strategy.on_day_end()
        
        # 7. 통계 확인
        stats = strategy.get_statistics()
        assert stats["total_signals"] == 2
        assert stats["executed_trades"] == 1
        assert stats["execution_rate"] == 0.5
        assert stats["initialized"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])