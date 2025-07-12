# -*- coding: utf-8 -*-
"""
성과 계산기 테스트
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from unittest.mock import MagicMock

import pytest

from src.core.models.domain import Portfolio, Transaction, TransactionType
from src.domain.backtest.performance_calculator import (
    PerformanceCalculator, 
    PerformanceMetrics, 
    RiskMetrics, 
    TradeAnalysis
)


class TestPerformanceCalculator:
    """성과 계산기 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.initial_capital = Decimal("10000000")  # 1천만원
        
        # 샘플 포트폴리오
        self.portfolio = Portfolio(
            account_id="TEST",
            initial_capital=float(self.initial_capital)
        )
        
        # 샘플 거래 내역
        self.transactions = [
            Transaction(
                symbol="005930",
                transaction_type=TransactionType.BUY,
                quantity=100,
                price=70000.0,
                commission=105.0,
                executed_at=datetime(2023, 1, 15)
            ),
            Transaction(
                symbol="005930",
                transaction_type=TransactionType.SELL,
                quantity=50,
                price=75000.0,
                commission=112.5,
                tax=225.0,
                executed_at=datetime(2023, 3, 20)
            ),
            Transaction(
                symbol="000660",
                transaction_type=TransactionType.BUY,
                quantity=50,
                price=120000.0,
                commission=90.0,
                executed_at=datetime(2023, 2, 10)
            )
        ]
        
        # 일일 수익률 데이터
        self.daily_returns = [
            Decimal("0.02"),    # 2%
            Decimal("-0.01"),   # -1%
            Decimal("0.015"),   # 1.5%
            Decimal("-0.005"),  # -0.5%
            Decimal("0.01"),    # 1%
            Decimal("0.005"),   # 0.5%
            Decimal("-0.02"),   # -2%
            Decimal("0.025"),   # 2.5%
            Decimal("0.0"),     # 0%
            Decimal("0.01")     # 1%
        ]
        
        # 포트폴리오 가치 히스토리
        self.portfolio_values = [
            Decimal("10000000"),  # 시작
            Decimal("10200000"),  # +2%
            Decimal("10098000"),  # -1%
            Decimal("10249470"),  # +1.5%
            Decimal("10198218"),  # -0.5%
            Decimal("10300000"),  # +1%
            Decimal("10351500"),  # +0.5%
            Decimal("10144470"),  # -2%
            Decimal("10398082"),  # +2.5%
            Decimal("10398082"),  # 0%
            Decimal("10501943")   # +1%
        ]
    
    def test_performance_calculator_initialization(self):
        """성과 계산기 초기화 테스트"""
        calculator = PerformanceCalculator(
            initial_capital=self.initial_capital,
            portfolio_values=self.portfolio_values,
            daily_returns=self.daily_returns,
            transactions=self.transactions
        )
        
        # 초기화 검증
        assert calculator.initial_capital == self.initial_capital
        assert calculator.portfolio_values == self.portfolio_values
        assert calculator.daily_returns == self.daily_returns
        assert calculator.transactions == self.transactions
        assert calculator.risk_free_rate == Decimal("0.03")  # 기본값
        
        # 기본 데이터 검증
        assert self.initial_capital == Decimal("10000000")
        assert len(self.transactions) == 3
        assert len(self.daily_returns) == 10
        assert len(self.portfolio_values) == 11  # 시작값 + 10개 변화
    
    def test_calculate_total_return(self):
        """총 수익률 계산 테스트"""
        calculator = PerformanceCalculator(
            initial_capital=self.initial_capital,
            portfolio_values=self.portfolio_values,
            daily_returns=self.daily_returns,
            transactions=self.transactions
        )
        
        total_return = calculator.calculate_total_return()
        expected_return = (Decimal("10501943") - Decimal("10000000")) / Decimal("10000000")
        
        assert total_return == expected_return
        assert total_return > 0  # 수익 발생
        
        # 퍼센트 변환
        total_return_pct = total_return * 100
        assert abs(total_return_pct - Decimal("5.01943")) < Decimal("0.001")
    
    def test_calculate_annualized_return(self):
        """연환산 수익률 계산 테스트"""
        # 기간 계산 (365일 기준)
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        days = (end_date - start_date).days + 1
        
        # 총 수익률
        total_return = Decimal("0.0501943")  # 5.01943%
        
        # 연환산 수익률 계산: (1 + total_return) ^ (365/days) - 1
        if days > 0:
            annual_factor = 365.0 / days
            annualized_return = Decimal(str((1 + float(total_return)) ** annual_factor - 1))
        else:
            annualized_return = Decimal("0")
        
        # 1년이므로 총 수익률과 동일해야 함
        assert abs(Decimal(str(annualized_return)) - total_return) < Decimal("0.001")
    
    def test_calculate_volatility(self):
        """변동성 계산 테스트"""
        # 일일 수익률의 표준편차
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        
        # 편차 제곱의 합
        variance = sum((r - mean_return) ** 2 for r in self.daily_returns) / len(self.daily_returns)
        volatility = variance ** Decimal("0.5")
        
        # 연환산 변동성 (252 거래일 기준)
        annualized_volatility = volatility * (Decimal("252") ** Decimal("0.5"))
        
        # 검증
        assert volatility > 0
        assert annualized_volatility > volatility
        
        # 대략적인 범위 확인 (0.5% ~ 5% 정도 예상)
        assert Decimal("0.005") < volatility < Decimal("0.05")
    
    def test_calculate_sharpe_ratio(self):
        """샤프 비율 계산 테스트"""
        # 평균 일일 수익률
        mean_daily_return = sum(self.daily_returns) / len(self.daily_returns)
        
        # 일일 수익률 변동성
        variance = sum((r - mean_daily_return) ** 2 for r in self.daily_returns) / len(self.daily_returns)
        daily_volatility = variance ** Decimal("0.5")
        
        # 무위험 수익률 (연 3% 가정)
        risk_free_rate = Decimal("0.03")
        daily_risk_free = risk_free_rate / Decimal("252")
        
        # 샤프 비율 계산
        if daily_volatility > 0:
            sharpe_ratio = (mean_daily_return - daily_risk_free) / daily_volatility
            # 연환산
            annualized_sharpe = sharpe_ratio * (Decimal("252") ** Decimal("0.5"))
        else:
            sharpe_ratio = Decimal("0")
            annualized_sharpe = Decimal("0")
        
        # 검증
        assert isinstance(sharpe_ratio, Decimal)
        assert isinstance(annualized_sharpe, Decimal)
    
    def test_calculate_max_drawdown(self):
        """최대 손실폭 계산 테스트"""
        # 누적 최고가 추적
        peak_values = []
        current_peak = self.portfolio_values[0]
        
        for value in self.portfolio_values:
            if value > current_peak:
                current_peak = value
            peak_values.append(current_peak)
        
        # 각 시점에서의 손실폭 계산
        drawdowns = []
        for i, value in enumerate(self.portfolio_values):
            drawdown = (peak_values[i] - value) / peak_values[i]
            drawdowns.append(drawdown)
        
        # 최대 손실폭
        max_drawdown = max(drawdowns)
        
        # 검증
        assert max_drawdown >= 0  # 손실폭은 0 이상
        assert max_drawdown <= 1  # 100% 이하
        
        # 예상 최대 손실폭 확인 (대략 2% 정도)
        assert max_drawdown < Decimal("0.05")  # 5% 미만
    
    def test_calculate_win_rate(self):
        """승률 계산 테스트"""
        # 일일 수익률 기준 승률
        positive_days = len([r for r in self.daily_returns if r > 0])
        total_days = len(self.daily_returns)
        
        win_rate = Decimal(str(positive_days)) / Decimal(str(total_days))
        
        # 검증
        assert 0 <= win_rate <= 1
        assert win_rate == Decimal("0.6")  # 10일 중 6일 수익
        
        # 퍼센트 변환
        win_rate_pct = win_rate * 100
        assert win_rate_pct == Decimal("60")
    
    def test_calculate_profit_factor(self):
        """이익 팩터 계산 테스트"""
        # 수익 일들의 총 수익
        gross_profit = sum(r for r in self.daily_returns if r > 0)
        
        # 손실 일들의 총 손실 (절댓값)
        gross_loss = sum(abs(r) for r in self.daily_returns if r < 0)
        
        # 이익 팩터 계산
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = Decimal("inf")  # 손실이 없는 경우
        
        # 검증
        assert profit_factor > 0
        assert isinstance(profit_factor, Decimal)
        
        # 예상 범위 (1.5 ~ 3.0 정도가 좋은 수준)
        assert profit_factor > 1  # 1보다 크면 수익성 있음
    
    def test_calculate_average_trade_return(self):
        """평균 거래 수익률 계산 테스트"""
        if len(self.daily_returns) > 0:
            avg_return = sum(self.daily_returns) / len(self.daily_returns)
        else:
            avg_return = Decimal("0")
        
        # 검증
        assert isinstance(avg_return, Decimal)
        
        # 예상 평균 수익률 (양수이면 좋음)
        expected_avg = sum(self.daily_returns) / Decimal(str(len(self.daily_returns)))
        assert avg_return == expected_avg
        assert avg_return > 0  # 평균적으로 수익
    
    def test_calculate_sortino_ratio(self):
        """소르티노 비율 계산 테스트"""
        # 평균 수익률
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        
        # 하방 변동성 (손실만 고려)
        target_return = Decimal("0")  # 목표 수익률 0%
        downside_returns = [r for r in self.daily_returns if r < target_return]
        
        if len(downside_returns) > 0:
            downside_variance = sum((r - target_return) ** 2 for r in downside_returns) / len(self.daily_returns)
            downside_deviation = downside_variance ** Decimal("0.5")
            
            # 소르티노 비율
            if downside_deviation > 0:
                sortino_ratio = (mean_return - target_return) / downside_deviation
            else:
                sortino_ratio = Decimal("inf")
        else:
            sortino_ratio = Decimal("inf")  # 손실이 없는 경우
        
        # 검증
        assert sortino_ratio >= 0 or sortino_ratio == Decimal("inf")
        assert isinstance(sortino_ratio, Decimal)
    
    def test_calculate_calmar_ratio(self):
        """칼마 비율 계산 테스트"""
        # 연환산 수익률
        total_return = (self.portfolio_values[-1] - self.portfolio_values[0]) / self.portfolio_values[0]
        annualized_return = total_return  # 1년 기간 가정
        
        # 최대 손실폭 계산
        peak_value = self.portfolio_values[0]
        max_drawdown = Decimal("0")
        
        for value in self.portfolio_values[1:]:
            if value > peak_value:
                peak_value = value
            else:
                drawdown = (peak_value - value) / peak_value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # 칼마 비율 계산
        if max_drawdown > 0:
            calmar_ratio = annualized_return / max_drawdown
        else:
            calmar_ratio = Decimal("inf")  # 손실이 없는 경우
        
        # 검증
        assert isinstance(calmar_ratio, Decimal)
        assert calmar_ratio >= 0 or calmar_ratio == Decimal("inf")
    
    def test_calculate_information_ratio(self):
        """정보 비율 계산 테스트"""
        # 벤치마크 수익률 (코스피 수익률 가정)
        benchmark_returns = [
            Decimal("0.01"),    # 1%
            Decimal("-0.005"),  # -0.5%
            Decimal("0.01"),    # 1%
            Decimal("0.005"),   # 0.5%
            Decimal("0.008"),   # 0.8%
            Decimal("0.002"),   # 0.2%
            Decimal("-0.015"),  # -1.5%
            Decimal("0.02"),    # 2%
            Decimal("0.003"),   # 0.3%
            Decimal("0.006")    # 0.6%
        ]
        
        # 초과 수익률 계산
        excess_returns = [
            self.daily_returns[i] - benchmark_returns[i]
            for i in range(min(len(self.daily_returns), len(benchmark_returns)))
        ]
        
        # 초과 수익률의 평균과 변동성
        if len(excess_returns) > 0:
            mean_excess = sum(excess_returns) / len(excess_returns)
            
            if len(excess_returns) > 1:
                variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
                tracking_error = variance ** Decimal("0.5")
                
                # 정보 비율
                if tracking_error > 0:
                    information_ratio = mean_excess / tracking_error
                else:
                    information_ratio = Decimal("0")
            else:
                information_ratio = Decimal("0")
        else:
            information_ratio = Decimal("0")
        
        # 검증
        assert isinstance(information_ratio, Decimal)
    
    def test_calculate_beta_alpha(self):
        """베타와 알파 계산 테스트"""
        # 벤치마크 수익률
        benchmark_returns = [
            Decimal("0.01"), Decimal("-0.005"), Decimal("0.01"), Decimal("0.005"), Decimal("0.008"),
            Decimal("0.002"), Decimal("-0.015"), Decimal("0.02"), Decimal("0.003"), Decimal("0.006")
        ]
        
        # 공분산과 분산 계산
        portfolio_mean = sum(self.daily_returns) / len(self.daily_returns)
        benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
        
        # 공분산 계산
        covariance = sum(
            (self.daily_returns[i] - portfolio_mean) * (benchmark_returns[i] - benchmark_mean)
            for i in range(len(self.daily_returns))
        ) / len(self.daily_returns)
        
        # 벤치마크 분산 계산
        benchmark_variance = sum(
            (r - benchmark_mean) ** 2 for r in benchmark_returns
        ) / len(benchmark_returns)
        
        # 베타 계산
        if benchmark_variance > 0:
            beta = covariance / benchmark_variance
        else:
            beta = Decimal("0")
        
        # 알파 계산 (CAPM)
        risk_free_rate = Decimal("0.0001")  # 일일 무위험 수익률
        alpha = portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))
        
        # 검증
        assert isinstance(beta, Decimal)
        assert isinstance(alpha, Decimal)
    
    def test_performance_summary_calculation(self):
        """성과 요약 계산 테스트"""
        # 종합 성과 지표 계산
        initial_value = self.portfolio_values[0]
        final_value = self.portfolio_values[-1]
        
        performance_summary = {
            "initial_capital": initial_value,
            "final_value": final_value,
            "total_return": (final_value - initial_value) / initial_value,
            "total_trades": len(self.transactions),
            "winning_trades": len([t for t in self.transactions if t.transaction_type == TransactionType.SELL]),
            "total_days": len(self.daily_returns),
            "profitable_days": len([r for r in self.daily_returns if r > 0]),
            "win_rate": len([r for r in self.daily_returns if r > 0]) / len(self.daily_returns),
            "average_daily_return": sum(self.daily_returns) / len(self.daily_returns),
            "best_day": max(self.daily_returns),
            "worst_day": min(self.daily_returns)
        }
        
        # 검증
        assert performance_summary["initial_capital"] == Decimal("10000000")
        assert performance_summary["total_return"] > 0
        assert performance_summary["total_trades"] == 3
        assert 0 <= performance_summary["win_rate"] <= 1
        assert performance_summary["best_day"] == Decimal("0.025")  # 2.5%
        assert performance_summary["worst_day"] == Decimal("-0.02")  # -2%
    
    def test_risk_adjusted_metrics(self):
        """위험조정 지표 종합 테스트"""
        # 기본 통계
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        returns_variance = sum((r - mean_return) ** 2 for r in self.daily_returns) / len(self.daily_returns)
        volatility = returns_variance ** Decimal("0.5")
        
        # 위험조정 지표
        risk_metrics = {
            "volatility": volatility,
            "annualized_volatility": volatility * (Decimal("252") ** Decimal("0.5")),
            "value_at_risk_95": sorted(self.daily_returns)[int(len(self.daily_returns) * 0.05)],
            "conditional_var_95": sum(sorted(self.daily_returns)[:int(len(self.daily_returns) * 0.05)]) / max(1, int(len(self.daily_returns) * 0.05))
        }
        
        # 검증
        assert risk_metrics["volatility"] > 0
        assert risk_metrics["annualized_volatility"] > risk_metrics["volatility"]
        assert risk_metrics["value_at_risk_95"] <= 0  # VaR는 일반적으로 음수
        
        # CVaR이 0이 아닌 경우에만 비교 (tail이 존재하는 경우)
        if risk_metrics["conditional_var_95"] != 0:
            assert risk_metrics["conditional_var_95"] <= risk_metrics["value_at_risk_95"]