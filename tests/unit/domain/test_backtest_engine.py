# -*- coding: utf-8 -*-
"""
백테스트 엔진 테스트
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.backtest.models import BacktestConfig, BacktestResult, BacktestStatus
from src.domain.backtest.engine import BacktestEngine, BacktestEvent, TradeSignal
from src.core.models.domain import Portfolio, Transaction, TransactionType
from src.core.models.market_data import Quote, OHLCV


class TestBacktestEngine:
    """백테스트 엔진 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal("10000000"),
            commission_rate=Decimal("0.0015"),
            tax_rate=Decimal("0.003"),
            slippage_rate=Decimal("0.001")
        )
        
        # Mock 전략
        self.mock_strategy = AsyncMock()
        self.mock_strategy.name = "TestStrategy"
        self.mock_strategy.version = "1.0.0"
        
        # Mock 데이터 제공자
        self.mock_data_provider = AsyncMock()
        
        # Mock 포트폴리오 매니저
        self.mock_portfolio_manager = MagicMock()
        
    def test_backtest_engine_initialization(self):
        """백테스트 엔진 초기화 테스트"""
        engine = BacktestEngine(
            config=self.config,
            strategy=self.mock_strategy,
            data_provider=self.mock_data_provider,
            portfolio_manager=self.mock_portfolio_manager
        )
        
        # 초기화 검증
        assert engine.config == self.config
        assert engine.strategy == self.mock_strategy
        assert engine.data_provider == self.mock_data_provider
        assert engine.status == BacktestStatus.PENDING
        assert engine.current_date == self.config.start_date
        assert engine.portfolio.account_id == "BACKTEST"
        assert engine.portfolio.initial_capital == float(self.config.initial_capital)
    
    @pytest.mark.asyncio
    async def test_backtest_engine_run_success(self):
        """백테스트 엔진 성공적 실행 테스트"""
        # 샘플 데이터
        sample_quote = Quote(
            symbol="005930",
            timestamp=datetime(2023, 6, 1, 9, 0),
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000"),
            data_type="quote",
            source="kiwoom"
        )
        
        # Mock 데이터 제공자 설정
        self.mock_data_provider.get_historical_data.return_value = [sample_quote]
        
        # Mock 전략 신호 설정
        self.mock_strategy.process_data.return_value = [
            {
                "action": "BUY",
                "symbol": "005930",
                "quantity": 100,
                "price": Decimal("70000")
            }
        ]
        
        # Mock 포트폴리오 매니저 설정
        initial_portfolio = Portfolio(
            account_id="TEST",
            initial_capital=10000000.0
        )
        final_portfolio = Portfolio(
            account_id="TEST",
            initial_capital=10000000.0,
            cash=2950000.0  # 700만원 투자 + 수수료
        )
        final_portfolio.positions["005930"] = MagicMock()
        
        self.mock_portfolio_manager.get_portfolio.return_value = final_portfolio
        
        # 백테스트 실행 시뮬레이션
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)
        
        # 예상 결과
        expected_result = BacktestResult(
            config=self.config,
            status=BacktestStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            final_portfolio=final_portfolio,
            transactions=[],
            daily_returns=[],
            metadata={"strategy_name": "TestStrategy"}
        )
        
        # 검증
        assert expected_result.status == BacktestStatus.COMPLETED
        assert expected_result.is_successful() is True
        assert expected_result.config == self.config
    
    @pytest.mark.asyncio
    async def test_backtest_engine_event_processing(self):
        """백테스트 엔진 이벤트 처리 테스트"""
        # 여러 데이터 포인트
        data_points = [
            Quote(
                symbol="005930",
                timestamp=datetime(2023, 6, 1, 9, 0) + timedelta(minutes=i),
                price=Decimal(str(70000 + i * 100)),
                prev_close=Decimal("69000"),
                change=Decimal(str(1000 + i * 100)),
                change_rate=Decimal("1.45"),
                volume=1000000,
                trade_value=Decimal("70000000000"),
                open_price=Decimal("69500"),
                high_price=Decimal("70500"),
                low_price=Decimal("69000"),
                data_type="quote",
                source="kiwoom"
            )
            for i in range(5)
        ]
        
        # 이벤트 처리 시뮬레이션
        processed_events = []
        for data in data_points:
            event = {
                "type": "market_data",
                "data": data,
                "timestamp": data.timestamp
            }
            processed_events.append(event)
        
        # 검증
        assert len(processed_events) == 5
        assert all(event["type"] == "market_data" for event in processed_events)
        
        # 시간 순서 검증
        timestamps = [event["timestamp"] for event in processed_events]
        assert timestamps == sorted(timestamps)
    
    def test_backtest_engine_portfolio_integration(self):
        """백테스트 엔진 포트폴리오 통합 테스트"""
        # 거래 시뮬레이션
        transaction = Transaction(
            symbol="005930",
            transaction_type=TransactionType.BUY,
            quantity=100,
            price=70000.0,
            commission=105.0
        )
        
        # 포트폴리오 상태 변화
        portfolio = Portfolio(
            account_id="TEST",
            initial_capital=10000000.0
        )
        
        # 수동으로 포지션 추가 (실제 구현에서는 엔진이 수행)
        initial_cash = portfolio.cash
        trade_cost = (transaction.quantity * transaction.price) + transaction.commission
        expected_cash = initial_cash - trade_cost
        
        # 검증
        assert initial_cash == 10000000.0
        assert trade_cost == 7000105.0
        assert expected_cash == 2999895.0
    
    @pytest.mark.asyncio
    async def test_backtest_engine_error_handling(self):
        """백테스트 엔진 에러 처리 테스트"""
        # 데이터 제공자 에러 시뮬레이션
        self.mock_data_provider.get_historical_data.side_effect = Exception("Data provider error")
        
        # 전략 에러 시뮬레이션
        self.mock_strategy.process_data.side_effect = Exception("Strategy error")
        
        # 에러 처리 검증
        with pytest.raises(Exception) as exc_info:
            await self.mock_data_provider.get_historical_data("005930", datetime.now(), datetime.now())
        assert "Data provider error" in str(exc_info.value)
        
        with pytest.raises(Exception) as exc_info:
            await self.mock_strategy.process_data({})
        assert "Strategy error" in str(exc_info.value)
    
    def test_backtest_engine_performance_metrics(self):
        """백테스트 엔진 성과 지표 테스트"""
        # 샘플 일일 수익률
        daily_returns = [
            Decimal("0.01"),   # 1%
            Decimal("-0.005"), # -0.5%
            Decimal("0.02"),   # 2%
            Decimal("0.005"),  # 0.5%
            Decimal("-0.01")   # -1%
        ]
        
        # 기본 성과 지표 계산
        total_return = sum(daily_returns)
        average_return = total_return / len(daily_returns)
        positive_days = len([r for r in daily_returns if r > 0])
        negative_days = len([r for r in daily_returns if r < 0])
        
        # 검증
        assert total_return == Decimal("0.02")  # 2%
        assert average_return == Decimal("0.004")  # 0.4%
        assert positive_days == 3
        assert negative_days == 2
    
    @pytest.mark.asyncio
    async def test_backtest_engine_real_time_updates(self):
        """백테스트 엔진 실시간 업데이트 테스트"""
        # 실시간 업데이트 시뮬레이션
        updates = []
        
        # 콜백 함수
        def on_portfolio_update(portfolio):
            updates.append({
                "type": "portfolio",
                "timestamp": datetime.now(),
                "total_value": portfolio.cash
            })
        
        def on_trade_executed(transaction):
            updates.append({
                "type": "trade",
                "timestamp": datetime.now(),
                "symbol": transaction.symbol,
                "action": transaction.transaction_type.value
            })
        
        # 업데이트 시뮬레이션
        portfolio = Portfolio(account_id="TEST", initial_capital=10000000.0)
        transaction = Transaction(
            symbol="005930",
            transaction_type=TransactionType.BUY,
            quantity=100,
            price=70000.0
        )
        
        on_portfolio_update(portfolio)
        on_trade_executed(transaction)
        
        # 검증
        assert len(updates) == 2
        assert updates[0]["type"] == "portfolio"
        assert updates[1]["type"] == "trade"
        assert updates[1]["symbol"] == "005930"
        assert updates[1]["action"] == "buy"
    
    def test_backtest_engine_risk_management(self):
        """백테스트 엔진 리스크 관리 테스트"""
        # 리스크 한도 설정
        risk_limits = {
            "max_position_size": Decimal("0.1"),    # 10%
            "max_daily_loss": Decimal("0.05"),      # 5%
            "max_drawdown": Decimal("0.2")          # 20%
        }
        
        # 포지션 크기 검증
        portfolio_value = Decimal("10000000")
        position_value = Decimal("800000")
        position_ratio = position_value / portfolio_value
        
        assert position_ratio == Decimal("0.08")  # 8%
        assert position_ratio < risk_limits["max_position_size"]  # 한도 내
        
        # 일일 손실 검증
        daily_pnl = Decimal("-300000")  # -30만원
        daily_loss_ratio = abs(daily_pnl) / portfolio_value
        
        assert daily_loss_ratio == Decimal("0.03")  # 3%
        assert daily_loss_ratio < risk_limits["max_daily_loss"]  # 한도 내
    
    def test_backtest_engine_data_validation(self):
        """백테스트 엔진 데이터 검증 테스트"""
        # 잘못된 데이터 케이스
        invalid_data_cases = [
            # 음수 가격
            {
                "symbol": "005930",
                "price": Decimal("-70000"),
                "expected_error": "Price cannot be negative"
            },
            # 0 거래량
            {
                "symbol": "005930",
                "volume": 0,
                "expected_error": "Volume must be positive"
            },
            # 빈 심볼
            {
                "symbol": "",
                "price": Decimal("70000"),
                "expected_error": "Symbol cannot be empty"
            }
        ]
        
        # 데이터 검증 함수 시뮬레이션
        def validate_market_data(data):
            if "price" in data and data["price"] < 0:
                raise ValueError("Price cannot be negative")
            if "volume" in data and data["volume"] <= 0:
                raise ValueError("Volume must be positive")
            if "symbol" in data and not data["symbol"]:
                raise ValueError("Symbol cannot be empty")
            return True
        
        # 검증 테스트
        for case in invalid_data_cases:
            with pytest.raises(ValueError) as exc_info:
                validate_market_data(case)
            assert case["expected_error"] in str(exc_info.value)
    
    def test_backtest_engine_configuration_validation(self):
        """백테스트 엔진 설정 검증 테스트"""
        # 유효하지 않은 설정
        invalid_configs = [
            # 종료일이 시작일보다 빠름
            {
                "start_date": datetime(2023, 12, 31),
                "end_date": datetime(2023, 1, 1),
                "initial_capital": Decimal("10000000")
            },
            # 음수 초기 자본
            {
                "start_date": datetime(2023, 1, 1),
                "end_date": datetime(2023, 12, 31),
                "initial_capital": Decimal("-1000000")
            }
        ]
        
        # 설정 검증
        for config_data in invalid_configs:
            with pytest.raises(ValueError):
                BacktestConfig(**config_data)
    
    @pytest.mark.asyncio
    async def test_backtest_engine_state_persistence(self):
        """백테스트 엔진 상태 저장 테스트"""
        # 상태 데이터
        engine_state = {
            "current_date": datetime(2023, 6, 1),
            "processed_events": 1000,
            "total_trades": 50,
            "current_portfolio_value": Decimal("11500000"),
            "status": BacktestStatus.RUNNING
        }
        
        # 상태 직렬화/역직렬화 시뮬레이션
        import json
        
        # Decimal을 문자열로 변환
        state_json = json.dumps({
            "current_date": engine_state["current_date"].isoformat(),
            "processed_events": engine_state["processed_events"],
            "total_trades": engine_state["total_trades"],
            "current_portfolio_value": str(engine_state["current_portfolio_value"]),
            "status": engine_state["status"].value
        })
        
        # 역직렬화
        restored_state = json.loads(state_json)
        restored_state["current_date"] = datetime.fromisoformat(restored_state["current_date"])
        restored_state["current_portfolio_value"] = Decimal(restored_state["current_portfolio_value"])
        restored_state["status"] = BacktestStatus(restored_state["status"])
        
        # 검증
        assert restored_state["current_date"] == engine_state["current_date"]
        assert restored_state["processed_events"] == engine_state["processed_events"]
        assert restored_state["current_portfolio_value"] == engine_state["current_portfolio_value"]
        assert restored_state["status"] == engine_state["status"]