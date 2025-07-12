# -*- coding: utf-8 -*-
"""
백테스트 모델 테스트
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

import pytest

from src.domain.backtest.models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus
)
from src.core.models.domain import Portfolio, Transaction, Position, TransactionType


class TestBacktestModels:
    """백테스트 모델 테스트"""
    
    def test_backtest_config_creation(self):
        """백테스트 설정 생성 테스트"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal("10000000"),  # 1천만원
            commission_rate=Decimal("0.0015"),    # 0.15%
            tax_rate=Decimal("0.003"),            # 0.3%
            slippage_rate=Decimal("0.001")        # 0.1%
        )
        
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.initial_capital == Decimal("10000000")
        assert config.commission_rate == Decimal("0.0015")
        assert config.tax_rate == Decimal("0.003")
        assert config.slippage_rate == Decimal("0.001")
    
    def test_backtest_config_validation(self):
        """백테스트 설정 검증 테스트"""
        # 잘못된 날짜 순서
        with pytest.raises(ValueError) as exc_info:
            BacktestConfig(
                start_date=datetime(2023, 12, 31),
                end_date=datetime(2023, 1, 1),  # 시작일보다 이른 종료일
                initial_capital=Decimal("10000000")
            )
        assert "end_date must be after start_date" in str(exc_info.value)
        
        # 음수 초기 자본
        with pytest.raises(ValueError) as exc_info:
            BacktestConfig(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                initial_capital=Decimal("-1000000")  # 음수 자본
            )
        assert "initial_capital must be positive" in str(exc_info.value)
    
    def test_backtest_config_duration(self):
        """백테스트 기간 계산 테스트"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 31),
            initial_capital=Decimal("10000000")
        )
        
        assert config.duration_days == 30
    
    def test_backtest_result_creation(self):
        """백테스트 결과 생성 테스트"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal("10000000")
        )
        
        # 샘플 포트폴리오
        portfolio = Portfolio(
            account_id="TEST_ACCOUNT",
            initial_capital=10000000.0,
            cash=5000000.0
        )
        
        # 샘플 거래 내역
        transactions = [
            Transaction(
                symbol="005930",
                transaction_type=TransactionType.BUY,
                quantity=100,
                price=70000.0,
                commission=105.0
            )
        ]
        
        result = BacktestResult(
            config=config,
            status=BacktestStatus.COMPLETED,
            start_time=datetime(2023, 1, 1, 9, 0),
            end_time=datetime(2023, 1, 1, 15, 30),
            final_portfolio=portfolio,
            transactions=transactions,
            daily_returns=[],
            metadata={"strategy_name": "TestStrategy"}
        )
        
        assert result.config == config
        assert result.status == BacktestStatus.COMPLETED
        assert result.final_portfolio == portfolio
        assert len(result.transactions) == 1
        assert result.metadata["strategy_name"] == "TestStrategy"
    
    def test_backtest_result_performance_calculation(self):
        """백테스트 결과 성과 계산 테스트"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal("10000000")
        )
        
        # 최종 포트폴리오 (20% 수익)
        portfolio = Portfolio(
            account_id="TEST_ACCOUNT",
            initial_capital=10000000.0,
            cash=12000000.0  # 2백만원 수익
        )
        
        result = BacktestResult(
            config=config,
            status=BacktestStatus.COMPLETED,
            start_time=datetime(2023, 1, 1, 9, 0),
            end_time=datetime(2023, 1, 1, 15, 30),
            final_portfolio=portfolio,
            transactions=[],
            daily_returns=[],
            metadata={}
        )
        
        # 총 수익률 계산
        total_return = result.calculate_total_return()
        assert total_return == Decimal("0.2")  # 20%
        
        # 총 가치 계산
        total_value = result.calculate_total_value()
        assert total_value == Decimal("12000000")
        
        # 절대 수익 계산
        absolute_profit = result.calculate_absolute_profit()
        assert absolute_profit == Decimal("2000000")
    
    def test_backtest_status_enum(self):
        """백테스트 상태 열거형 테스트"""
        assert BacktestStatus.PENDING.value == "pending"
        assert BacktestStatus.RUNNING.value == "running"
        assert BacktestStatus.COMPLETED.value == "completed"
        assert BacktestStatus.FAILED.value == "failed"
        assert BacktestStatus.CANCELLED.value == "cancelled"
    
    def test_backtest_result_execution_time(self):
        """백테스트 실행 시간 계산 테스트"""
        start_time = datetime(2023, 1, 1, 9, 0, 0)
        end_time = datetime(2023, 1, 1, 9, 5, 30)  # 5분 30초 후
        
        result = BacktestResult(
            config=BacktestConfig(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                initial_capital=Decimal("10000000")
            ),
            status=BacktestStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            final_portfolio=Portfolio(
                account_id="TEST",
                initial_capital=10000000.0,
                cash=10000000.0
            ),
            transactions=[],
            daily_returns=[],
            metadata={}
        )
        
        execution_time = result.execution_time_seconds
        assert execution_time == 330.0  # 5분 30초 = 330초
    
    def test_backtest_result_with_positions(self):
        """포지션이 있는 백테스트 결과 테스트"""
        # 포지션이 있는 포트폴리오
        position = Position(
            symbol="005930",
            quantity=100,
            average_price=70000.0
        )
        
        portfolio = Portfolio(
            account_id="TEST_ACCOUNT",
            initial_capital=10000000.0,
            cash=2500000.0  # 250만원 현금
        )
        portfolio.positions["005930"] = position
        
        result = BacktestResult(
            config=BacktestConfig(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                initial_capital=Decimal("10000000")
            ),
            status=BacktestStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            final_portfolio=portfolio,
            transactions=[],
            daily_returns=[],
            metadata={}
        )
        
        # 총 가치: 현금 + 포지션 가치 (평균가 기준)
        total_value = result.calculate_total_value()
        expected_value = Decimal("2500000") + (Decimal("70000") * 100)  # 250만 + 700만
        assert total_value == expected_value  # 950만원
        
        # 수익률 확인 (950만원 / 1000만원 = -5%)
        total_return = result.calculate_total_return()
        assert total_return == Decimal("-0.05")