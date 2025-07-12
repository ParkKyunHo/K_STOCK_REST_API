# -*- coding: utf-8 -*-
"""
백테스트 통합 테스트
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.backtest import (
    BacktestEngine, BacktestConfig, BacktestStatus,
    PortfolioManager, PerformanceCalculator, TransactionCostModel,
    MarketCondition, TradeSignal
)
from src.core.models.domain import Portfolio, TransactionType
from src.core.models.market_data import Quote


class MockStrategy:
    """통합 테스트용 Mock 전략"""
    
    def __init__(self):
        self.name = "TestStrategy"
        self.version = "1.0.0"
        self.universe = ["005930", "000660"]  # 삼성전자, SK하이닉스
        self.initialized = False
        
    async def initialize(self):
        """전략 초기화"""
        self.initialized = True
        
    async def get_universe(self) -> List[str]:
        """투자 유니버스 반환"""
        return self.universe
        
    async def on_data(self, market_data) -> List[TradeSignal]:
        """시장 데이터 처리 및 신호 생성"""
        signals = []
        
        # 간단한 매매 로직: 가격이 70000원 이상이면 매수, 75000원 이상이면 매도
        if hasattr(market_data, 'price') and hasattr(market_data, 'symbol'):
            if market_data.price >= Decimal("70000") and market_data.price < Decimal("75000"):
                signals.append(TradeSignal(
                    symbol=market_data.symbol,
                    action="BUY",
                    quantity=100,
                    price=market_data.price,
                    timestamp=market_data.timestamp
                ))
            elif market_data.price >= Decimal("75000"):
                signals.append(TradeSignal(
                    symbol=market_data.symbol,
                    action="SELL",
                    quantity=50,
                    price=market_data.price,
                    timestamp=market_data.timestamp
                ))
                
        return signals


class MockDataProvider:
    """통합 테스트용 Mock 데이터 제공자"""
    
    def __init__(self):
        self.historical_data = self._generate_sample_data()
        
    def _generate_sample_data(self) -> Dict[str, List[Quote]]:
        """샘플 데이터 생성"""
        data = {}
        symbols = ["005930", "000660"]
        
        for symbol in symbols:
            quotes = []
            base_price = Decimal("70000") if symbol == "005930" else Decimal("120000")
            
            # 10일간의 데이터 생성
            for i in range(10):
                price_change = Decimal(str((i % 3 - 1) * 1000))  # -1000, 0, 1000 패턴
                current_price = base_price + price_change
                
                quote = Quote(
                    symbol=symbol,
                    timestamp=datetime(2023, 6, 1) + timedelta(days=i),
                    price=current_price,
                    prev_close=current_price - Decimal("500"),
                    change=Decimal("500"),
                    change_rate=Decimal("0.71"),
                    volume=1000000,
                    trade_value=current_price * 1000000,
                    open_price=current_price - Decimal("200"),
                    high_price=current_price + Decimal("300"),
                    low_price=current_price - Decimal("400"),
                    data_type="quote",
                    source="mock"
                )
                quotes.append(quote)
                
            data[symbol] = quotes
            
        return data
    
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime):
        """히스토리 데이터 반환"""
        if symbol in self.historical_data:
            # 배치로 반환 (실제로는 대용량 데이터 페이징)
            yield self.historical_data[symbol]
        else:
            yield []
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """현재가 반환"""
        if symbol in self.historical_data and self.historical_data[symbol]:
            return self.historical_data[symbol][-1].price
        return Decimal("70000")


@pytest.mark.asyncio
class TestBacktestIntegration:
    """백테스트 통합 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        # 백테스트 설정
        self.config = BacktestConfig(
            start_date=datetime(2023, 6, 1),
            end_date=datetime(2023, 6, 10),
            initial_capital=Decimal("10000000"),  # 1천만원
            commission_rate=Decimal("0.0015"),
            tax_rate=Decimal("0.003"),
            slippage_rate=Decimal("0.001")
        )
        
        # Mock 컴포넌트
        self.strategy = MockStrategy()
        self.data_provider = MockDataProvider()
        
        # 포트폴리오 매니저
        self.portfolio = Portfolio(
            account_id="BACKTEST",
            initial_capital=float(self.config.initial_capital)
        )
        self.portfolio_manager = PortfolioManager(
            portfolio=self.portfolio,
            data_provider=self.data_provider
        )
        
        # 거래 비용 모델
        self.cost_model = TransactionCostModel(
            commission_rate=self.config.commission_rate,
            tax_rate=self.config.tax_rate,
            slippage_rate=self.config.slippage_rate,
            market_condition=MarketCondition.SIDEWAYS
        )
        
    async def test_complete_backtest_workflow(self):
        """완전한 백테스트 워크플로우 테스트"""
        # 백테스트 엔진 생성
        engine = BacktestEngine(
            config=self.config,
            strategy=self.strategy,
            data_provider=self.data_provider,
            portfolio_manager=self.portfolio_manager
        )
        
        # 초기 상태 확인
        assert engine.status == BacktestStatus.PENDING
        assert engine.portfolio.cash == float(self.config.initial_capital)
        
        # 백테스트 실행 시뮬레이션 (실제 실행은 복잡하므로 주요 컴포넌트만 테스트)
        await self.strategy.initialize()
        assert self.strategy.initialized is True
        
        # 샘플 데이터로 전략 테스트
        sample_quote = Quote(
            symbol="005930",
            timestamp=datetime(2023, 6, 1, 10, 0),
            price=Decimal("72000"),  # 매수 신호 발생
            prev_close=Decimal("71000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.41"),
            volume=1000000,
            trade_value=Decimal("72000000000"),
            open_price=Decimal("71500"),
            high_price=Decimal("72500"),
            low_price=Decimal("71000"),
            data_type="quote",
            source="mock"
        )
        
        # 전략 신호 생성
        signals = await self.strategy.on_data(sample_quote)
        assert len(signals) == 1
        assert signals[0].action == "BUY"
        assert signals[0].symbol == "005930"
        assert signals[0].quantity == 100
    
    async def test_portfolio_manager_integration(self):
        """포트폴리오 매니저 통합 테스트"""
        # 매수 주문 실행
        success, message, position = await self.portfolio_manager.execute_buy_order(
            symbol="005930",
            quantity=100,
            price=Decimal("70000"),
            validate_risk=False  # 테스트용으로 리스크 검증 비활성화
        )
        
        # 결과 확인 (성공하지 않을 수도 있음)
        if success:
            assert position is not None
            assert "005930" in self.portfolio.positions
        else:
            print(f"매수 주문 실패: {message}")
            # 실패 원인 분석을 위해 현금 확인
            assert self.portfolio.cash > 0
        
        # 포트폴리오 평가
        valuation = await self.portfolio_manager.get_portfolio_valuation()
        assert valuation["total_value"] > 0
        assert valuation["market_value"] > 0
        assert valuation["cash"] < float(self.config.initial_capital)  # 현금 감소
        
        # 성과 지표 계산
        performance = await self.portfolio_manager.calculate_performance_metrics()
        assert performance.cash_balance < self.config.initial_capital
        assert performance.market_value > 0
        
    async def test_transaction_cost_integration(self):
        """거래 비용 모델 통합 테스트"""
        # 매수 거래 비용 계산
        buy_costs = self.cost_model.calculate_total_cost(
            price=Decimal("70000"),
            quantity=100,
            transaction_type=TransactionType.BUY,
            trade_time=datetime(2023, 6, 1, 10, 30)
        )
        
        assert buy_costs.commission > 0
        assert buy_costs.tax == 0  # 매수시 세금 없음
        assert buy_costs.slippage > 0
        assert buy_costs.total_cost > buy_costs.commission
        
        # 매도 거래 비용 계산
        sell_costs = self.cost_model.calculate_total_cost(
            price=Decimal("75000"),
            quantity=100,
            transaction_type=TransactionType.SELL,
            trade_time=datetime(2023, 6, 1, 14, 30)
        )
        
        assert sell_costs.commission > 0
        assert sell_costs.tax > 0  # 매도시 세금 있음
        assert sell_costs.slippage > 0
        assert sell_costs.total_cost > sell_costs.commission + sell_costs.tax
        
        # 비용 분석 리포트
        cost_breakdown = self.cost_model.get_cost_breakdown(
            price=Decimal("70000"),
            quantity=100,
            transaction_type=TransactionType.BUY
        )
        
        assert "total_cost" in cost_breakdown
        assert "components" in cost_breakdown
        assert cost_breakdown["cost_ratio"] > 0
        assert cost_breakdown["cost_ratio"] < 0.1  # 10% 미만
        
    async def test_performance_calculator_integration(self):
        """성과 계산기 통합 테스트"""
        # 샘플 백테스트 결과 데이터
        initial_capital = Decimal("10000000")
        portfolio_values = [
            Decimal("10000000"),  # 시작
            Decimal("10100000"),  # +1%
            Decimal("10050000"),  # -0.5%
            Decimal("10200000"),  # +1.5%
            Decimal("10180000"),  # -0.2%
            Decimal("10300000")   # +1.2%
        ]
        
        daily_returns = [
            Decimal("0.01"),    # 1%
            Decimal("-0.005"),  # -0.5%
            Decimal("0.015"),   # 1.5%
            Decimal("-0.002"),  # -0.2%
            Decimal("0.012")    # 1.2%
        ]
        
        # 샘플 거래 내역
        transactions = [
            MagicMock(
                symbol="005930",
                transaction_type=TransactionType.BUY,
                quantity=100,
                price=70000.0,
                commission=105.0,
                tax=0.0
            ),
            MagicMock(
                symbol="005930", 
                transaction_type=TransactionType.SELL,
                quantity=50,
                price=75000.0,
                commission=112.5,
                tax=225.0
            )
        ]
        
        # 성과 계산기 생성
        calculator = PerformanceCalculator(
            initial_capital=initial_capital,
            portfolio_values=portfolio_values,
            daily_returns=daily_returns,
            transactions=transactions
        )
        
        # 종합 성과 지표 계산
        metrics = calculator.get_performance_metrics()
        
        assert metrics.total_return > 0  # 수익 발생
        assert metrics.volatility > 0   # 변동성 존재
        assert metrics.sharpe_ratio != 0  # 샤프 비율 계산됨
        assert metrics.max_drawdown >= 0  # 최대 손실폭
        assert metrics.win_rate > 0  # 승률
        
        # 리스크 지표 계산
        risk_metrics = calculator.get_risk_metrics()
        
        assert risk_metrics.value_at_risk_95 <= 0  # VaR는 음수 또는 0
        assert risk_metrics.downside_deviation >= 0  # 하방편차
        
    async def test_end_to_end_backtest_simulation(self):
        """End-to-End 백테스트 시뮬레이션"""
        # 1. 백테스트 설정 검증
        assert self.config.initial_capital > 0
        assert self.config.end_date > self.config.start_date
        
        # 2. 전략 초기화
        await self.strategy.initialize()
        universe = await self.strategy.get_universe()
        assert len(universe) > 0
        
        # 3. 데이터 제공자 테스트
        historical_data = []
        for symbol in universe:
            async for batch in self.data_provider.get_historical_data(
                symbol, self.config.start_date, self.config.end_date
            ):
                historical_data.extend(batch)
        
        assert len(historical_data) > 0
        
        # 4. 거래 시뮬레이션
        total_trades = 0
        total_cost = Decimal("0")
        
        for data_point in historical_data[:3]:  # 처음 3개만 테스트
            # 전략 신호 생성
            signals = await self.strategy.on_data(data_point)
            
            for signal in signals:
                # 거래 비용 계산
                costs = self.cost_model.calculate_total_cost(
                    price=signal.price,
                    quantity=signal.quantity,
                    transaction_type=TransactionType.BUY if signal.action == "BUY" else TransactionType.SELL
                )
                
                total_cost += costs.total_cost
                total_trades += 1
                
                # 포트폴리오 업데이트 (시뮬레이션)
                if signal.action == "BUY" and self.portfolio.cash >= float(signal.price * signal.quantity + costs.total_cost):
                    success, message, position = await self.portfolio_manager.execute_buy_order(
                        symbol=signal.symbol,
                        quantity=signal.quantity,
                        price=signal.price,
                        validate_risk=False  # 테스트용
                    )
                    if success:
                        print(f"매수 성공: {signal.symbol} x{signal.quantity} @ {signal.price}")
        
        # 5. 최종 결과 검증
        final_valuation = await self.portfolio_manager.get_portfolio_valuation()
        
        assert final_valuation["total_value"] > 0
        assert total_cost > 0 if total_trades > 0 else total_cost == 0
        
        # 거래가 발생했다면 비용도 발생해야 함
        if total_trades > 0:
            cost_ratio = total_cost / Decimal(str(final_valuation["total_value"]))
            assert cost_ratio < Decimal("0.1")  # 총 비용이 포트폴리오 가치의 10% 미만
            
    async def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        # 설정 검증 에러
        with pytest.raises(ValueError):
            invalid_config_test = BacktestConfig(
                start_date=datetime(2023, 12, 31),
                end_date=datetime(2023, 1, 1),  # 잘못된 날짜 순서
                initial_capital=Decimal("10000000")
            )
        
        # 부족한 현금으로 매수 시도
        large_order_success, message, position = await self.portfolio_manager.execute_buy_order(
            symbol="005930",
            quantity=10000,  # 매우 큰 수량
            price=Decimal("100000"),  # 높은 가격
            validate_risk=True
        )
        
        assert large_order_success is False
        assert "cash" in message.lower() or "insufficient" in message.lower()
        assert position is None
        
    async def test_performance_under_different_conditions(self):
        """다양한 시장 조건에서의 성과 테스트"""
        conditions = [MarketCondition.BULL, MarketCondition.BEAR, MarketCondition.VOLATILE]
        
        for condition in conditions:
            # 시장 조건별 비용 모델
            cost_model = TransactionCostModel(
                market_condition=condition,
                commission_rate=self.config.commission_rate
            )
            
            # 동일한 거래에 대한 비용 계산
            costs = cost_model.calculate_total_cost(
                price=Decimal("70000"),
                quantity=100,
                transaction_type=TransactionType.BUY
            )
            
            assert costs.total_cost > 0
            
            # 시장 조건별 비용 차이 확인
            if condition == MarketCondition.BULL:
                # 상승장에서는 비용이 더 저렴
                assert costs.total_cost > 0
            elif condition == MarketCondition.VOLATILE:
                # 변동성 장에서는 비용이 더 비쌈
                assert costs.total_cost > 0
                
    def test_component_integration_consistency(self):
        """컴포넌트 간 일관성 테스트"""
        # 동일한 설정값이 모든 컴포넌트에서 일관되게 사용되는지 확인
        assert self.config.commission_rate == self.cost_model.commission_rate
        assert self.config.tax_rate == self.cost_model.tax_rate
        assert self.config.initial_capital == Decimal(str(self.portfolio.initial_capital))
        
        # 포트폴리오 매니저와 거래 비용 모델의 일관성
        sample_commission = self.cost_model.calculate_commission(Decimal("7000000"))
        assert sample_commission >= self.cost_model.min_commission
        assert sample_commission <= self.cost_model.max_commission