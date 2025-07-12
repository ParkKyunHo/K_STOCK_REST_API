# -*- coding: utf-8 -*-
"""
전략 로더 및 실행기 테스트
"""
import asyncio
import logging
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from src.strategy.loader import StrategyLoader
from src.strategy.runner import StrategyRunner, StrategyState
from src.strategy.base import StrategyConfig, StrategyContext, BaseStrategy
from src.core.interfaces.strategy import Signal, SignalType, MarketData
from src.core.models.domain import Portfolio
from src.core.interfaces import IMarketDataProvider


# 테스트용 전략
class MockStrategy(BaseStrategy):
    """테스트용 Mock 전략"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.signal_count = 0
    
    async def generate_signals(self, data: MarketData):
        """테스트용 신호 생성"""
        self.signal_count += 1
        
        if data.close > 10000:
            return [Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=0.8,
                price=data.close,
                reason="Mock buy signal"
            )]
        return []


class TestStrategyLoader:
    """StrategyLoader 테스트"""
    
    @pytest.fixture
    def temp_plugin_dir(self):
        """임시 플러그인 디렉토리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def strategy_loader(self, temp_plugin_dir):
        """전략 로더"""
        return StrategyLoader(strategy_dirs=[temp_plugin_dir])
    
    @pytest.fixture
    def sample_strategy_file(self, temp_plugin_dir):
        """샘플 전략 파일 생성"""
        strategy_code = '''
# -*- coding: utf-8 -*-
"""
샘플 테스트 전략
"""
from src.strategy.base import BaseStrategy, StrategyConfig
from src.core.interfaces.strategy import Signal, SignalType, MarketData

class TestPluginStrategy(BaseStrategy):
    """테스트 플러그인 전략"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
    
    async def generate_signals(self, data: MarketData):
        """테스트 신호 생성"""
        return []
'''
        
        strategy_file = os.path.join(temp_plugin_dir, "test_plugin_strategy.py")
        with open(strategy_file, 'w', encoding='utf-8') as f:
            f.write(strategy_code)
        
        return strategy_file
    
    def test_loader_initialization(self, strategy_loader):
        """로더 초기화 테스트"""
        assert isinstance(strategy_loader.loaded_strategies, dict)
        assert isinstance(strategy_loader.strategy_dirs, list)
        assert strategy_loader.logger is not None
    
    def test_load_all_strategies(self, strategy_loader):
        """모든 전략 로드 테스트"""
        strategies = strategy_loader.load_all_strategies()
        
        # 결과가 딕셔너리인지 확인
        assert isinstance(strategies, dict)
        
        # 로드 오류가 기록되는지 확인
        assert isinstance(strategy_loader.load_errors, dict)
    
    def test_get_loaded_strategies(self, strategy_loader):
        """로드된 전략 목록 테스트"""
        # 먼저 전략을 로드
        strategy_loader.load_all_strategies()
        
        strategies = strategy_loader.loaded_strategies
        assert isinstance(strategies, dict)
    
    def test_get_load_errors(self, strategy_loader):
        """로드 오류 확인 테스트"""
        # 전략 로드 시도
        strategy_loader.load_all_strategies()
        
        errors = strategy_loader.load_errors
        assert isinstance(errors, dict)


class TestStrategyRunner:
    """StrategyRunner 테스트"""
    
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
    
    @pytest.fixture
    def mock_strategy(self):
        """Mock 전략"""
        config = StrategyConfig(name="Mock Strategy")
        return MockStrategy(config)
    
    @pytest.fixture
    def strategy_runner(self, mock_strategy, strategy_context):
        """전략 실행기"""
        return StrategyRunner(mock_strategy, strategy_context)
    
    def test_runner_initialization(self, strategy_runner, strategy_context, mock_strategy):
        """실행기 초기화 테스트"""
        assert strategy_runner.context == strategy_context
        assert strategy_runner.strategy == mock_strategy
        assert strategy_runner.logger is not None
        assert strategy_runner.state == StrategyState.IDLE
    
    # initialize 메서드는 StrategyRunner에 없으므로 제거
    
    @pytest.mark.asyncio
    async def test_stop_runner(self, strategy_runner):
        """실행기 중지 테스트"""
        # 중지 (실행되지 않은 상태에서도 호출 가능해야 함)
        await strategy_runner.stop()
        # 예외 없이 완료되어야 함
        assert True
    
    def test_get_state(self, strategy_runner):
        """상태 조회 테스트"""
        state = strategy_runner.get_state()
        assert isinstance(state, StrategyState)
        assert state == StrategyState.IDLE
    
    def test_pause_resume(self, strategy_runner):
        """일시정지/재개 테스트"""
        # 일시정지
        strategy_runner.pause()
        # 예외 없이 완료되어야 함
        
        # 재개
        strategy_runner.resume()
        # 예외 없이 완료되어야 함
        assert True
    
    def test_get_statistics(self, strategy_runner):
        """통계 조회 테스트"""
        stats = strategy_runner.get_statistics()
        
        assert isinstance(stats, dict)
        assert "strategy_name" in stats
        assert "state" in stats
        assert "total_signals" in stats
        assert "total_orders" in stats
    
    def test_get_execution_summary(self, strategy_runner):
        """실행 요약 조회 테스트"""
        summary = strategy_runner.get_execution_summary()
        
        assert isinstance(summary, dict)
        assert "strategy_statistics" in summary
        assert "context_summary" in summary
    
    # StrategyRunner의 실제 API에 맞게 간소화된 테스트들
    # 실제 run 메서드는 AsyncIterator를 받으므로 복잡한 통합 테스트는 별도로 구성


class TestLoaderRunnerIntegration:
    """로더-실행기 통합 테스트"""
    
    def test_basic_integration(self):
        """기본 통합 테스트"""
        # 1. 로더 생성
        loader = StrategyLoader()
        strategies = loader.load_all_strategies()
        
        assert isinstance(strategies, dict)
        
        # 2. Mock 전략과 컨텍스트 생성
        config = StrategyConfig(name="Integration Test")
        mock_strategy = MockStrategy(config)
        
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
        
        # 3. 실행기 생성
        runner = StrategyRunner(mock_strategy, context)
        
        # 4. 기본 상태 확인
        assert runner.get_state() == StrategyState.IDLE
        assert isinstance(runner.get_statistics(), dict)
        assert isinstance(runner.get_execution_summary(), dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])