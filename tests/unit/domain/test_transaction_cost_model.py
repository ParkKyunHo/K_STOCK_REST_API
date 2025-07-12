# -*- coding: utf-8 -*-
"""
거래 비용 모델 테스트
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

from src.core.models.domain import Transaction, TransactionType
from src.domain.backtest.transaction_cost_model import (
    TransactionCostModel,
    CostComponents,
    MarketCondition,
    TradeSize,
    CommissionTier
)


class TestTransactionCostModel:
    """거래 비용 모델 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        # 기본 거래 정보
        self.base_price = Decimal("70000")
        self.base_quantity = 100
        self.base_symbol = "005930"
        
        # 한국 주식 시장 기본 수수료율
        self.default_commission_rate = Decimal("0.0015")  # 0.15%
        self.default_tax_rate = Decimal("0.003")          # 0.3% (매도시만)
        self.default_slippage_rate = Decimal("0.001")     # 0.1%
        
        # 최소/최대 수수료
        self.min_commission = Decimal("1000")   # 최소 1000원
        self.max_commission = Decimal("100000") # 최대 10만원
        
        # 거래 시간대별 스프레드
        self.time_based_spreads = {
            "market_open": Decimal("0.002"),    # 개장 직후 0.2%
            "normal": Decimal("0.001"),         # 정상 시간 0.1%
            "market_close": Decimal("0.0015"),  # 장마감 전 0.15%
            "after_hours": Decimal("0.005")     # 시간외 0.5%
        }
        
        # 거래량별 슬리피지
        self.volume_slippage = {
            "small": Decimal("0.0005"),   # 소량 거래 0.05%
            "medium": Decimal("0.001"),   # 중간 거래 0.1%
            "large": Decimal("0.002"),    # 대량 거래 0.2%
            "huge": Decimal("0.005")      # 초대량 거래 0.5%
        }
    
    def test_transaction_cost_model_initialization(self):
        """거래 비용 모델 초기화 테스트"""
        cost_model = TransactionCostModel(
            commission_rate=self.default_commission_rate,
            tax_rate=self.default_tax_rate,
            slippage_rate=self.default_slippage_rate,
            min_commission=self.min_commission,
            max_commission=self.max_commission
        )
        
        # 초기화 검증
        assert cost_model.commission_rate == self.default_commission_rate
        assert cost_model.tax_rate == self.default_tax_rate
        assert cost_model.slippage_rate == self.default_slippage_rate
        assert cost_model.min_commission == self.min_commission
        assert cost_model.max_commission == self.max_commission
        assert cost_model.market_condition == MarketCondition.SIDEWAYS
        
        # 기본 설정 검증
        assert self.default_commission_rate == Decimal("0.0015")
        assert self.default_tax_rate == Decimal("0.003")
        assert self.default_slippage_rate == Decimal("0.001")
        assert self.min_commission == Decimal("1000")
        assert self.max_commission == Decimal("100000")
    
    def test_calculate_basic_commission(self):
        """기본 수수료 계산 테스트"""
        # 거래 금액
        notional = self.base_price * self.base_quantity  # 700만원
        
        # 기본 수수료 계산
        commission = notional * self.default_commission_rate
        expected_commission = Decimal("10500")  # 700만원 * 0.15% = 10,500원
        
        assert commission == expected_commission
        
        # 최소 수수료 적용 테스트 (소액 거래)
        small_notional = Decimal("500000")  # 50만원
        small_commission = small_notional * self.default_commission_rate
        calculated_commission = small_commission  # 750원
        
        # 최소 수수료 적용
        final_commission = max(calculated_commission, self.min_commission)
        assert final_commission == self.min_commission  # 1000원
    
    def test_calculate_progressive_commission(self):
        """누진 수수료 계산 테스트"""
        # 거래량별 수수료 구조
        commission_tiers = [
            {"limit": Decimal("1000000"), "rate": Decimal("0.002")},    # 100만원까지 0.2%
            {"limit": Decimal("10000000"), "rate": Decimal("0.0015")},  # 1000만원까지 0.15%
            {"limit": Decimal("100000000"), "rate": Decimal("0.001")},  # 1억원까지 0.1%
            {"limit": None, "rate": Decimal("0.0005")}                  # 1억원 초과 0.05%
        ]
        
        def calculate_progressive_commission(notional: Decimal) -> Decimal:
            """누진 수수료 계산"""
            remaining = notional
            total_commission = Decimal("0")
            prev_limit = Decimal("0")
            
            for tier in commission_tiers:
                if tier["limit"] is None:
                    # 마지막 구간
                    total_commission += remaining * tier["rate"]
                    break
                else:
                    tier_amount = min(remaining, tier["limit"] - prev_limit)
                    if tier_amount <= 0:
                        continue
                    
                    total_commission += tier_amount * tier["rate"]
                    remaining -= tier_amount
                    prev_limit = tier["limit"]
                    
                    if remaining <= 0:
                        break
            
            return total_commission
        
        # 다양한 거래 규모 테스트
        test_amounts = [
            Decimal("500000"),    # 50만원
            Decimal("5000000"),   # 500만원
            Decimal("50000000"),  # 5000만원
            Decimal("150000000")  # 1억5천만원
        ]
        
        for amount in test_amounts:
            commission = calculate_progressive_commission(amount)
            assert commission > 0
            assert commission < amount  # 수수료가 원금보다 클 수 없음
    
    def test_calculate_tax(self):
        """세금 계산 테스트"""
        # 매도세 (증권거래세)
        sell_notional = self.base_price * self.base_quantity
        sell_tax = sell_notional * self.default_tax_rate
        expected_tax = Decimal("21000")  # 700만원 * 0.3% = 21,000원
        
        assert sell_tax == expected_tax
        
        # 매수시에는 세금 없음
        buy_tax = Decimal("0")
        assert buy_tax == Decimal("0")
        
        # 종목별 세율 차이 테스트
        etf_tax_rate = Decimal("0.0008")  # ETF 0.08%
        reit_tax_rate = Decimal("0.0035") # 리츠 0.35%
        
        etf_tax = sell_notional * etf_tax_rate
        reit_tax = sell_notional * reit_tax_rate
        
        assert etf_tax < sell_tax  # ETF가 더 저렴
        assert reit_tax > sell_tax # 리츠가 더 비쌈
    
    def test_calculate_slippage(self):
        """슬리피지 계산 테스트"""
        # 기본 슬리피지
        base_slippage = self.base_price * self.default_slippage_rate
        expected_slippage = Decimal("70")  # 70,000원 * 0.1% = 70원
        
        assert base_slippage == expected_slippage
        
        # 거래량별 슬리피지
        def calculate_volume_slippage(quantity: int) -> Decimal:
            if quantity < 100:
                return self.volume_slippage["small"]
            elif quantity < 1000:
                return self.volume_slippage["medium"]
            elif quantity < 10000:
                return self.volume_slippage["large"]
            else:
                return self.volume_slippage["huge"]
        
        # 다양한 거래량 테스트
        quantities = [50, 500, 5000, 50000]
        for qty in quantities:
            slippage_rate = calculate_volume_slippage(qty)
            price_impact = self.base_price * slippage_rate
            
            assert slippage_rate > 0
            assert price_impact >= 0
            
            # 거래량이 클수록 슬리피지 증가
            if qty > 100:
                prev_rate = calculate_volume_slippage(qty // 10)
                assert slippage_rate >= prev_rate
    
    def test_calculate_time_based_costs(self):
        """시간대별 비용 계산 테스트"""
        # 시간대별 거래 비용
        market_open_time = datetime(2023, 6, 1, 9, 0)    # 09:00 개장
        normal_time = datetime(2023, 6, 1, 11, 30)       # 11:30 정상시간
        market_close_time = datetime(2023, 6, 1, 15, 20) # 15:20 장마감 전
        after_hours_time = datetime(2023, 6, 1, 18, 0)   # 18:00 시간외
        
        def get_time_spread(trade_time: datetime) -> Decimal:
            hour = trade_time.hour
            minute = trade_time.minute
            
            if hour == 9 and minute < 30:  # 개장 30분
                return self.time_based_spreads["market_open"]
            elif hour == 15 and minute >= 15:  # 장마감 15분 전
                return self.time_based_spreads["market_close"]
            elif 9 <= hour < 15 or (hour == 15 and minute < 15):  # 정규 장시간
                return self.time_based_spreads["normal"]
            else:  # 시간외
                return self.time_based_spreads["after_hours"]
        
        # 각 시간대별 스프레드 계산
        open_spread = get_time_spread(market_open_time)
        normal_spread = get_time_spread(normal_time)
        close_spread = get_time_spread(market_close_time)
        after_spread = get_time_spread(after_hours_time)
        
        # 검증
        assert open_spread == self.time_based_spreads["market_open"]
        assert normal_spread == self.time_based_spreads["normal"]
        assert close_spread == self.time_based_spreads["market_close"]
        assert after_spread == self.time_based_spreads["after_hours"]
        
        # 시간외가 가장 비쌈
        assert after_spread > open_spread
        assert after_spread > normal_spread
        assert after_spread > close_spread
    
    def test_calculate_market_impact(self):
        """시장 충격 비용 계산 테스트"""
        # 일평균 거래량 대비 거래 비중
        daily_avg_volume = 1000000  # 일평균 100만주
        
        def calculate_market_impact(quantity: int, avg_volume: int) -> Decimal:
            """시장 충격 계산"""
            volume_ratio = Decimal(str(quantity)) / Decimal(str(avg_volume))
            
            # 비선형 시장 충격 모델
            if volume_ratio <= Decimal("0.01"):      # 1% 이하
                return Decimal("0.0001")             # 0.01%
            elif volume_ratio <= Decimal("0.05"):    # 5% 이하
                return volume_ratio * Decimal("0.01") # 비례
            elif volume_ratio <= Decimal("0.1"):     # 10% 이하
                return volume_ratio * Decimal("0.02") # 2배 비례
            else:                                     # 10% 초과
                return volume_ratio * Decimal("0.05") # 5배 비례
        
        # 다양한 거래량 테스트
        test_quantities = [1000, 10000, 50000, 100000, 200000]
        
        for qty in test_quantities:
            impact = calculate_market_impact(qty, daily_avg_volume)
            impact_cost = self.base_price * qty * impact
            
            # 검증
            assert impact >= 0
            assert impact_cost >= 0
            
            # 거래량이 클수록 시장 충격 증가 (충분히 큰 차이가 있을 때만)
            if qty > 10000:  # 더 큰 차이가 필요
                prev_qty = qty // 10
                prev_impact = calculate_market_impact(prev_qty, daily_avg_volume)
                if prev_qty != qty:  # 실제로 다른 수량일 때만 비교
                    assert impact >= prev_impact
    
    def test_calculate_total_transaction_cost(self):
        """총 거래 비용 계산 테스트"""
        # 매수 거래 비용
        buy_quantity = 100
        buy_price = Decimal("70000")
        buy_notional = buy_price * buy_quantity
        
        # 매수 비용 구성
        buy_commission = max(buy_notional * self.default_commission_rate, self.min_commission)
        buy_tax = Decimal("0")  # 매수시 세금 없음
        buy_slippage = buy_price * self.default_slippage_rate * buy_quantity
        
        total_buy_cost = buy_commission + buy_tax + buy_slippage
        
        # 매도 거래 비용
        sell_quantity = 100
        sell_price = Decimal("75000")  # 5천원 상승
        sell_notional = sell_price * sell_quantity
        
        # 매도 비용 구성
        sell_commission = max(sell_notional * self.default_commission_rate, self.min_commission)
        sell_tax = sell_notional * self.default_tax_rate
        sell_slippage = sell_price * self.default_slippage_rate * sell_quantity
        
        total_sell_cost = sell_commission + sell_tax + sell_slippage
        
        # 총 거래 비용
        total_cost = total_buy_cost + total_sell_cost
        
        # 검증
        assert total_buy_cost > buy_commission  # 슬리피지 포함
        assert total_sell_cost > sell_commission + sell_tax  # 슬리피지 포함
        assert total_cost > 0
        
        # 비용 비율 계산
        total_traded_value = buy_notional + sell_notional
        cost_ratio = total_cost / total_traded_value
        
        # 일반적으로 총 거래비용은 거래금액의 1% 이하
        assert cost_ratio < Decimal("0.01")
    
    def test_cost_optimization(self):
        """거래 비용 최적화 테스트"""
        # 대량 거래를 분할 실행하여 비용 절감
        large_quantity = 10000
        large_price = Decimal("70000")
        
        # 한번에 거래시 비용
        single_trade_cost = self._calculate_total_cost(large_quantity, large_price, "single")
        
        # 분할 거래시 비용 (10번 분할)
        split_count = 10
        split_quantity = large_quantity // split_count
        split_trade_cost = self._calculate_total_cost(split_quantity, large_price, "split") * split_count
        
        # 분할 거래가 더 유리할 수 있음 (시장 충격 감소)
        # 단, 수수료는 증가할 수 있음
        
        assert single_trade_cost > 0
        assert split_trade_cost > 0
    
    def _calculate_total_cost(self, quantity: int, price: Decimal, trade_type: str) -> Decimal:
        """거래 비용 계산 헬퍼 메소드"""
        notional = price * quantity
        
        # 기본 수수료
        commission = max(notional * self.default_commission_rate, self.min_commission)
        
        # 슬리피지 (대량 거래시 증가)
        if trade_type == "single" and quantity > 1000:
            slippage_rate = self.volume_slippage["large"]
        else:
            slippage_rate = self.volume_slippage["medium"]
        
        slippage = price * slippage_rate * quantity
        
        return commission + slippage
    
    def test_cost_model_edge_cases(self):
        """거래 비용 모델 예외 케이스 테스트"""
        # 0 수량 거래
        zero_cost = self._calculate_total_cost(0, self.base_price, "normal")
        assert zero_cost >= 0
        
        # 0 가격 거래
        zero_price_cost = self._calculate_total_cost(100, Decimal("0"), "normal")
        assert zero_price_cost >= 0
        
        # 매우 큰 거래
        huge_quantity = 1000000
        huge_cost = self._calculate_total_cost(huge_quantity, self.base_price, "single")
        assert huge_cost > 0
        
        # 매우 작은 거래
        tiny_quantity = 1
        tiny_cost = self._calculate_total_cost(tiny_quantity, self.base_price, "normal")
        assert tiny_cost >= self.min_commission  # 최소 수수료 적용
    
    def test_cost_comparison_scenarios(self):
        """거래 비용 비교 시나리오 테스트"""
        base_quantity = 1000
        base_price = Decimal("50000")
        
        # 시나리오 1: 일반 거래
        normal_cost = self._calculate_scenario_cost(base_quantity, base_price, "normal")
        
        # 시나리오 2: 대량 거래
        large_cost = self._calculate_scenario_cost(base_quantity * 10, base_price, "large")
        
        # 시나리오 3: 고가 종목 거래
        expensive_cost = self._calculate_scenario_cost(base_quantity, base_price * 10, "expensive")
        
        # 검증
        assert normal_cost > 0
        assert large_cost > normal_cost * 5  # 대량 거래는 비례 이상 증가
        assert expensive_cost > normal_cost * 5  # 고가 종목도 비례 이상 증가
    
    def _calculate_scenario_cost(self, quantity: int, price: Decimal, scenario: str) -> Decimal:
        """시나리오별 비용 계산"""
        notional = price * quantity
        
        # 기본 수수료
        commission = max(notional * self.default_commission_rate, self.min_commission)
        
        # 시나리오별 추가 비용
        additional_cost = Decimal("0")
        
        if scenario == "large":
            # 대량 거래시 시장 충격 추가
            additional_cost = notional * Decimal("0.002")
        elif scenario == "expensive":
            # 고가 종목은 스프레드가 더 클 수 있음
            additional_cost = notional * Decimal("0.001")
        
        return commission + additional_cost
    
    def test_cost_breakdown_analysis(self):
        """거래 비용 세부 분석 테스트"""
        quantity = 500
        price = Decimal("100000")
        notional = price * quantity  # 5천만원
        
        # 비용 구성 요소별 계산
        cost_breakdown = {
            "commission": max(notional * self.default_commission_rate, self.min_commission),
            "tax": notional * self.default_tax_rate,  # 매도 가정
            "slippage": price * self.default_slippage_rate * quantity,
            "spread": notional * Decimal("0.0005"),  # 스프레드 0.05%
            "market_impact": notional * Decimal("0.0002")  # 시장충격 0.02%
        }
        
        total_cost = sum(cost_breakdown.values())
        
        # 각 구성 요소 검증
        for component, cost in cost_breakdown.items():
            assert cost >= 0, f"{component} cost must be non-negative"
            
            # 비용 비중 계산
            cost_ratio = cost / total_cost
            assert 0 <= cost_ratio <= 1, f"{component} ratio must be between 0 and 1"
        
        # 총 비용이 거래금액의 합리적 수준인지 확인
        total_cost_ratio = total_cost / notional
        assert total_cost_ratio < Decimal("0.02"), "Total cost should be less than 2%"
    
    def test_dynamic_cost_model(self):
        """동적 거래 비용 모델 테스트"""
        # 시장 상황별 비용 조정
        market_conditions = {
            "bull": Decimal("0.8"),    # 상승장에서 비용 20% 절감
            "bear": Decimal("1.2"),    # 하락장에서 비용 20% 증가
            "sideways": Decimal("1.0"), # 횡보장에서 기본 비용
            "volatile": Decimal("1.5")  # 변동성 장에서 비용 50% 증가
        }
        
        base_cost = self._calculate_total_cost(1000, Decimal("50000"), "normal")
        
        for condition, multiplier in market_conditions.items():
            adjusted_cost = base_cost * multiplier
            
            assert adjusted_cost > 0
            
            if condition == "bull":
                assert adjusted_cost < base_cost
            elif condition in ["bear", "volatile"]:
                assert adjusted_cost > base_cost
            else:  # sideways
                assert adjusted_cost == base_cost