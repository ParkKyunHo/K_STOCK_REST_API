# -*- coding: utf-8 -*-
"""
성과 계산기 구현
"""
import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from src.core.models.domain import Transaction, TransactionType


@dataclass
class PerformanceMetrics:
    """성과 지표 모음"""
    # 기본 수익률 지표
    total_return: Decimal
    annualized_return: Decimal
    average_daily_return: Decimal
    
    # 위험 지표
    volatility: Decimal
    annualized_volatility: Decimal
    max_drawdown: Decimal
    
    # 위험조정 수익률
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    
    # 거래 통계
    total_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    
    # 추가 통계
    best_day: Decimal
    worst_day: Decimal
    consecutive_wins: int
    consecutive_losses: int


@dataclass 
class RiskMetrics:
    """위험 지표 모음"""
    value_at_risk_95: Decimal
    value_at_risk_99: Decimal
    conditional_var_95: Decimal
    conditional_var_99: Decimal
    downside_deviation: Decimal
    upside_deviation: Decimal
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None


@dataclass
class TradeAnalysis:
    """거래 분석 결과"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    profit_factor: Decimal
    expectancy: Decimal


class PerformanceCalculator:
    """성과 계산기
    
    백테스트 결과의 다양한 성과 지표를 계산합니다:
    - 수익률 지표 (총수익률, 연환산수익률 등)
    - 위험 지표 (변동성, 최대손실폭 등)  
    - 위험조정 수익률 (샤프, 소르티노, 칼마 비율)
    - 거래 통계 (승률, 이익팩터 등)
    """
    
    def __init__(
        self,
        initial_capital: Decimal,
        portfolio_values: List[Decimal],
        daily_returns: List[Decimal],
        transactions: List[Transaction],
        benchmark_returns: Optional[List[Decimal]] = None,
        risk_free_rate: Decimal = Decimal("0.03")  # 연 3%
    ):
        self.initial_capital = initial_capital
        self.portfolio_values = portfolio_values
        self.daily_returns = daily_returns
        self.transactions = transactions
        self.benchmark_returns = benchmark_returns
        self.risk_free_rate = risk_free_rate
        
        # 계산된 지표 캐시
        self._metrics_cache: Optional[PerformanceMetrics] = None
        self._risk_cache: Optional[RiskMetrics] = None
        self._trade_analysis_cache: Optional[TradeAnalysis] = None
        
        self.logger = logging.getLogger(__name__)
        
        # 데이터 검증
        self._validate_data()
    
    def _validate_data(self):
        """입력 데이터 검증"""
        if len(self.portfolio_values) < 2:
            raise ValueError("Portfolio values must have at least 2 data points")
        
        if len(self.daily_returns) != len(self.portfolio_values) - 1:
            raise ValueError("Daily returns length must be portfolio values length - 1")
        
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
    
    def calculate_total_return(self) -> Decimal:
        """총 수익률 계산"""
        if len(self.portfolio_values) < 2:
            return Decimal("0")
        
        initial_value = self.portfolio_values[0]
        final_value = self.portfolio_values[-1]
        
        if initial_value <= 0:
            return Decimal("0")
        
        return (final_value - initial_value) / initial_value
    
    def calculate_annualized_return(self, trading_days: int = 252) -> Decimal:
        """연환산 수익률 계산"""
        if len(self.daily_returns) == 0:
            return Decimal("0")
        
        total_return = self.calculate_total_return()
        days = len(self.daily_returns)
        
        if days == 0:
            return Decimal("0")
        
        # (1 + total_return) ^ (trading_days / days) - 1
        try:
            annual_factor = float(trading_days) / float(days)
            annualized = (1 + float(total_return)) ** annual_factor - 1
            return Decimal(str(annualized)).quantize(Decimal("0.000001"))
        except (ValueError, OverflowError):
            return Decimal("0")
    
    def calculate_volatility(self, annualized: bool = False) -> Decimal:
        """변동성 계산"""
        if len(self.daily_returns) < 2:
            return Decimal("0")
        
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        variance = sum((r - mean_return) ** 2 for r in self.daily_returns) / len(self.daily_returns)
        
        try:
            volatility = Decimal(str(math.sqrt(float(variance))))
            
            if annualized:
                # 연환산 변동성 (252 거래일 기준)
                volatility = volatility * Decimal(str(math.sqrt(252)))
            
            return volatility.quantize(Decimal("0.000001"))
        except (ValueError, OverflowError):
            return Decimal("0")
    
    def calculate_max_drawdown(self) -> Tuple[Decimal, int, int]:
        """최대 손실폭 계산
        
        Returns:
            (최대손실폭, 시작인덱스, 끝인덱스)
        """
        if len(self.portfolio_values) < 2:
            return Decimal("0"), 0, 0
        
        max_drawdown = Decimal("0")
        peak_value = self.portfolio_values[0]
        peak_index = 0
        drawdown_start = 0
        drawdown_end = 0
        
        for i, value in enumerate(self.portfolio_values):
            if value > peak_value:
                peak_value = value
                peak_index = i
            else:
                drawdown = (peak_value - value) / peak_value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    drawdown_start = peak_index
                    drawdown_end = i
        
        return max_drawdown, drawdown_start, drawdown_end
    
    def calculate_sharpe_ratio(self, trading_days: int = 252) -> Decimal:
        """샤프 비율 계산"""
        if len(self.daily_returns) < 2:
            return Decimal("0")
        
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        volatility = self.calculate_volatility(annualized=False)
        
        if volatility == 0:
            return Decimal("0")
        
        # 일일 무위험 수익률
        daily_risk_free = self.risk_free_rate / trading_days
        
        # 샤프 비율
        excess_return = mean_return - daily_risk_free
        sharpe = excess_return / volatility
        
        # 연환산
        annualized_sharpe = sharpe * Decimal(str(math.sqrt(trading_days)))
        
        return annualized_sharpe.quantize(Decimal("0.000001"))
    
    def calculate_sortino_ratio(self, target_return: Decimal = Decimal("0"), trading_days: int = 252) -> Decimal:
        """소르티노 비율 계산"""
        if len(self.daily_returns) < 2:
            return Decimal("0")
        
        mean_return = sum(self.daily_returns) / len(self.daily_returns)
        
        # 하방편차 계산 (목표수익률 미달 수익률만 고려)
        downside_returns = [r for r in self.daily_returns if r < target_return]
        
        if len(downside_returns) == 0:
            return Decimal("inf")  # 손실이 없는 경우
        
        downside_variance = sum((r - target_return) ** 2 for r in downside_returns) / len(self.daily_returns)
        
        try:
            downside_deviation = Decimal(str(math.sqrt(float(downside_variance))))
            
            if downside_deviation == 0:
                return Decimal("inf")
            
            sortino = (mean_return - target_return) / downside_deviation
            
            # 연환산
            annualized_sortino = sortino * Decimal(str(math.sqrt(trading_days)))
            
            return annualized_sortino.quantize(Decimal("0.000001"))
        except (ValueError, OverflowError):
            return Decimal("0")
    
    def calculate_calmar_ratio(self) -> Decimal:
        """칼마 비율 계산 (연환산수익률 / 최대손실폭)"""
        annualized_return = self.calculate_annualized_return()
        max_drawdown, _, _ = self.calculate_max_drawdown()
        
        if max_drawdown == 0:
            return Decimal("inf") if annualized_return > 0 else Decimal("0")
        
        return (annualized_return / max_drawdown).quantize(Decimal("0.000001"))
    
    def calculate_win_rate(self) -> Decimal:
        """승률 계산 (양수 수익률 비율)"""
        if len(self.daily_returns) == 0:
            return Decimal("0")
        
        winning_days = len([r for r in self.daily_returns if r > 0])
        return (Decimal(str(winning_days)) / Decimal(str(len(self.daily_returns)))).quantize(Decimal("0.0001"))
    
    def calculate_profit_factor(self) -> Decimal:
        """이익 팩터 계산 (총수익 / 총손실)"""
        gross_profit = sum(r for r in self.daily_returns if r > 0)
        gross_loss = sum(abs(r) for r in self.daily_returns if r < 0)
        
        if gross_loss == 0:
            return Decimal("inf") if gross_profit > 0 else Decimal("0")
        
        return (gross_profit / gross_loss).quantize(Decimal("0.000001"))
    
    def calculate_value_at_risk(self, confidence_level: Decimal = Decimal("0.95")) -> Decimal:
        """VaR 계산"""
        if len(self.daily_returns) == 0:
            return Decimal("0")
        
        sorted_returns = sorted(self.daily_returns)
        index = int(len(sorted_returns) * (1 - confidence_level))
        
        if index >= len(sorted_returns):
            index = len(sorted_returns) - 1
        
        return sorted_returns[index]
    
    def calculate_conditional_var(self, confidence_level: Decimal = Decimal("0.95")) -> Decimal:
        """조건부 VaR 계산 (Expected Shortfall)"""
        if len(self.daily_returns) == 0:
            return Decimal("0")
        
        var = self.calculate_value_at_risk(confidence_level)
        tail_returns = [r for r in self.daily_returns if r <= var]
        
        if len(tail_returns) == 0:
            return var
        
        return sum(tail_returns) / len(tail_returns)
    
    def calculate_beta_alpha(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """베타와 알파 계산 (벤치마크 대비)"""
        if self.benchmark_returns is None or len(self.benchmark_returns) != len(self.daily_returns):
            return None, None
        
        if len(self.daily_returns) < 2:
            return None, None
        
        # 평균 계산
        portfolio_mean = sum(self.daily_returns) / len(self.daily_returns)
        benchmark_mean = sum(self.benchmark_returns) / len(self.benchmark_returns)
        
        # 공분산과 분산 계산
        covariance = sum(
            (self.daily_returns[i] - portfolio_mean) * (self.benchmark_returns[i] - benchmark_mean)
            for i in range(len(self.daily_returns))
        ) / len(self.daily_returns)
        
        benchmark_variance = sum(
            (r - benchmark_mean) ** 2 for r in self.benchmark_returns
        ) / len(self.benchmark_returns)
        
        if benchmark_variance == 0:
            return None, None
        
        # 베타 계산
        beta = covariance / benchmark_variance
        
        # 알파 계산 (CAPM)
        daily_risk_free = self.risk_free_rate / 252
        alpha = portfolio_mean - (daily_risk_free + beta * (benchmark_mean - daily_risk_free))
        
        return beta.quantize(Decimal("0.000001")), alpha.quantize(Decimal("0.000001"))
    
    def analyze_trades(self) -> TradeAnalysis:
        """거래 분석"""
        if self._trade_analysis_cache is not None:
            return self._trade_analysis_cache
        
        if len(self.transactions) == 0:
            return TradeAnalysis(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=Decimal("0"),
                average_win=Decimal("0"),
                average_loss=Decimal("0"),
                largest_win=Decimal("0"),
                largest_loss=Decimal("0"),
                profit_factor=Decimal("0"),
                expectancy=Decimal("0")
            )
        
        # 매도 거래만 분석 (실현 손익)
        sell_trades = [t for t in self.transactions if t.transaction_type == TransactionType.SELL]
        
        if len(sell_trades) == 0:
            return TradeAnalysis(
                total_trades=len(self.transactions),
                winning_trades=0,
                losing_trades=0,
                win_rate=Decimal("0"),
                average_win=Decimal("0"),
                average_loss=Decimal("0"),
                largest_win=Decimal("0"),
                largest_loss=Decimal("0"),
                profit_factor=Decimal("0"),
                expectancy=Decimal("0")
            )
        
        # 간단한 손익 계산 (실제로는 더 복잡한 로직 필요)
        trade_pnls = []
        for trade in sell_trades:
            # 여기서는 단순히 가격 변화로 추정
            # 실제로는 매수가격과 연결해야 함
            pnl = Decimal(str(trade.price * trade.quantity - trade.commission - (trade.tax or 0)))
            trade_pnls.append(pnl)
        
        # 통계 계산
        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl < 0]
        
        total_trades = len(sell_trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = Decimal(str(win_count)) / Decimal(str(total_trades)) if total_trades > 0 else Decimal("0")
        
        average_win = sum(winning_trades) / len(winning_trades) if winning_trades else Decimal("0")
        average_loss = sum(losing_trades) / len(losing_trades) if losing_trades else Decimal("0")
        
        largest_win = max(winning_trades) if winning_trades else Decimal("0")
        largest_loss = min(losing_trades) if losing_trades else Decimal("0")
        
        gross_profit = sum(winning_trades) if winning_trades else Decimal("0")
        gross_loss = abs(sum(losing_trades)) if losing_trades else Decimal("1")  # 0으로 나누기 방지
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("0")
        expectancy = sum(trade_pnls) / len(trade_pnls) if trade_pnls else Decimal("0")
        
        analysis = TradeAnalysis(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            expectancy=expectancy
        )
        
        self._trade_analysis_cache = analysis
        return analysis
    
    def calculate_consecutive_periods(self) -> Tuple[int, int]:
        """연속 수익/손실 기간 계산"""
        if len(self.daily_returns) == 0:
            return 0, 0
        
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for return_val in self.daily_returns:
            if return_val > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif return_val < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0
        
        return max_consecutive_wins, max_consecutive_losses
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """종합 성과 지표 계산"""
        if self._metrics_cache is not None:
            return self._metrics_cache
        
        try:
            # 기본 수익률 지표
            total_return = self.calculate_total_return()
            annualized_return = self.calculate_annualized_return()
            average_daily_return = sum(self.daily_returns) / len(self.daily_returns) if self.daily_returns else Decimal("0")
            
            # 위험 지표
            volatility = self.calculate_volatility(annualized=False)
            annualized_volatility = self.calculate_volatility(annualized=True)
            max_drawdown, _, _ = self.calculate_max_drawdown()
            
            # 위험조정 수익률
            sharpe_ratio = self.calculate_sharpe_ratio()
            sortino_ratio = self.calculate_sortino_ratio()
            calmar_ratio = self.calculate_calmar_ratio()
            
            # 거래 통계
            trade_analysis = self.analyze_trades()
            win_rate = self.calculate_win_rate()
            profit_factor = self.calculate_profit_factor()
            
            # 추가 통계
            best_day = max(self.daily_returns) if self.daily_returns else Decimal("0")
            worst_day = min(self.daily_returns) if self.daily_returns else Decimal("0")
            consecutive_wins, consecutive_losses = self.calculate_consecutive_periods()
            
            metrics = PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                average_daily_return=average_daily_return,
                volatility=volatility,
                annualized_volatility=annualized_volatility,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                total_trades=trade_analysis.total_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                best_day=best_day,
                worst_day=worst_day,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses
            )
            
            self._metrics_cache = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {str(e)}")
            # 기본값으로 반환
            return PerformanceMetrics(
                total_return=Decimal("0"),
                annualized_return=Decimal("0"),
                average_daily_return=Decimal("0"),
                volatility=Decimal("0"),
                annualized_volatility=Decimal("0"),
                max_drawdown=Decimal("0"),
                sharpe_ratio=Decimal("0"),
                sortino_ratio=Decimal("0"),
                calmar_ratio=Decimal("0"),
                total_trades=0,
                win_rate=Decimal("0"),
                profit_factor=Decimal("0"),
                best_day=Decimal("0"),
                worst_day=Decimal("0"),
                consecutive_wins=0,
                consecutive_losses=0
            )
    
    def get_risk_metrics(self) -> RiskMetrics:
        """위험 지표 계산"""
        if self._risk_cache is not None:
            return self._risk_cache
        
        try:
            var_95 = self.calculate_value_at_risk(Decimal("0.95"))
            var_99 = self.calculate_value_at_risk(Decimal("0.99"))
            cvar_95 = self.calculate_conditional_var(Decimal("0.95"))
            cvar_99 = self.calculate_conditional_var(Decimal("0.99"))
            
            # 하방/상방 편차 계산
            mean_return = sum(self.daily_returns) / len(self.daily_returns) if self.daily_returns else Decimal("0")
            downside_returns = [r for r in self.daily_returns if r < mean_return]
            upside_returns = [r for r in self.daily_returns if r > mean_return]
            
            downside_deviation = Decimal("0")
            if downside_returns:
                downside_variance = sum((r - mean_return) ** 2 for r in downside_returns) / len(downside_returns)
                downside_deviation = Decimal(str(math.sqrt(float(downside_variance))))
            
            upside_deviation = Decimal("0")
            if upside_returns:
                upside_variance = sum((r - mean_return) ** 2 for r in upside_returns) / len(upside_returns)
                upside_deviation = Decimal(str(math.sqrt(float(upside_variance))))
            
            beta, alpha = self.calculate_beta_alpha()
            
            risk_metrics = RiskMetrics(
                value_at_risk_95=var_95,
                value_at_risk_99=var_99,
                conditional_var_95=cvar_95,
                conditional_var_99=cvar_99,
                downside_deviation=downside_deviation,
                upside_deviation=upside_deviation,
                beta=beta,
                alpha=alpha
            )
            
            self._risk_cache = risk_metrics
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {str(e)}")
            return RiskMetrics(
                value_at_risk_95=Decimal("0"),
                value_at_risk_99=Decimal("0"),
                conditional_var_95=Decimal("0"),
                conditional_var_99=Decimal("0"),
                downside_deviation=Decimal("0"),
                upside_deviation=Decimal("0"),
                beta=None,
                alpha=None
            )
    
    def generate_performance_report(self) -> Dict[str, any]:
        """성과 리포트 생성"""
        metrics = self.get_performance_metrics()
        risk_metrics = self.get_risk_metrics()
        trade_analysis = self.analyze_trades()
        
        return {
            "summary": {
                "initial_capital": float(self.initial_capital),
                "final_value": float(self.portfolio_values[-1]) if self.portfolio_values else 0,
                "total_return_pct": float(metrics.total_return * 100),
                "annualized_return_pct": float(metrics.annualized_return * 100),
                "max_drawdown_pct": float(metrics.max_drawdown * 100),
                "sharpe_ratio": float(metrics.sharpe_ratio),
                "win_rate_pct": float(metrics.win_rate * 100)
            },
            "performance_metrics": {
                "total_return": float(metrics.total_return),
                "annualized_return": float(metrics.annualized_return),
                "volatility": float(metrics.volatility),
                "max_drawdown": float(metrics.max_drawdown),
                "sharpe_ratio": float(metrics.sharpe_ratio),
                "sortino_ratio": float(metrics.sortino_ratio),
                "calmar_ratio": float(metrics.calmar_ratio),
                "best_day": float(metrics.best_day),
                "worst_day": float(metrics.worst_day)
            },
            "risk_metrics": {
                "var_95": float(risk_metrics.value_at_risk_95),
                "var_99": float(risk_metrics.value_at_risk_99),
                "cvar_95": float(risk_metrics.conditional_var_95),
                "downside_deviation": float(risk_metrics.downside_deviation),
                "beta": float(risk_metrics.beta) if risk_metrics.beta else None,
                "alpha": float(risk_metrics.alpha) if risk_metrics.alpha else None
            },
            "trade_analysis": {
                "total_trades": trade_analysis.total_trades,
                "win_rate": float(trade_analysis.win_rate),
                "profit_factor": float(trade_analysis.profit_factor),
                "average_win": float(trade_analysis.average_win),
                "average_loss": float(trade_analysis.average_loss),
                "largest_win": float(trade_analysis.largest_win),
                "largest_loss": float(trade_analysis.largest_loss)
            }
        }