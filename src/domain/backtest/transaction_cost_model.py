# -*- coding: utf-8 -*-
"""
거래 비용 모델 구현
"""
import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from src.core.models.domain import Transaction, TransactionType


class MarketCondition(Enum):
    """시장 상황"""
    BULL = "bull"           # 상승장
    BEAR = "bear"           # 하락장
    SIDEWAYS = "sideways"   # 횡보장
    VOLATILE = "volatile"   # 변동성 장


class TradeSize(Enum):
    """거래 규모"""
    SMALL = "small"     # 소량
    MEDIUM = "medium"   # 중간
    LARGE = "large"     # 대량
    HUGE = "huge"       # 초대량


@dataclass
class CostComponents:
    """거래 비용 구성 요소"""
    commission: Decimal         # 수수료
    tax: Decimal               # 세금
    slippage: Decimal          # 슬리피지
    spread: Decimal            # 스프레드
    market_impact: Decimal     # 시장 충격
    other_fees: Decimal        # 기타 수수료
    
    @property
    def total_cost(self) -> Decimal:
        """총 비용"""
        return (self.commission + self.tax + self.slippage + 
                self.spread + self.market_impact + self.other_fees)


@dataclass
class CommissionTier:
    """수수료 구간"""
    limit: Optional[Decimal]    # 구간 한도 (None은 무제한)
    rate: Decimal              # 수수료율


@dataclass
class TradingSession:
    """거래 세션 정보"""
    start_time: datetime
    end_time: datetime
    spread_multiplier: Decimal
    liquidity_factor: Decimal


class TransactionCostModel:
    """거래 비용 모델
    
    다양한 거래 비용을 계산합니다:
    - 수수료 (기본/누진/최소/최대)
    - 세금 (매도세, 종목별 차등)
    - 슬리피지 (거래량/시간대별)
    - 스프레드 (시장 상황별)
    - 시장 충격 (거래 규모별)
    """
    
    def __init__(
        self,
        commission_rate: Decimal = Decimal("0.0015"),      # 기본 수수료율 0.15%
        tax_rate: Decimal = Decimal("0.003"),              # 기본 세율 0.3%
        slippage_rate: Decimal = Decimal("0.001"),         # 기본 슬리피지 0.1%
        min_commission: Decimal = Decimal("1000"),         # 최소 수수료 1,000원
        max_commission: Decimal = Decimal("100000"),       # 최대 수수료 100,000원
        commission_tiers: Optional[List[CommissionTier]] = None,
        market_condition: MarketCondition = MarketCondition.SIDEWAYS
    ):
        self.commission_rate = commission_rate
        self.tax_rate = tax_rate
        self.slippage_rate = slippage_rate
        self.min_commission = min_commission
        self.max_commission = max_commission
        self.market_condition = market_condition
        
        # 누진 수수료 구조
        self.commission_tiers = commission_tiers or [
            CommissionTier(Decimal("1000000"), Decimal("0.002")),     # 100만원까지 0.2%
            CommissionTier(Decimal("10000000"), Decimal("0.0015")),   # 1000만원까지 0.15%
            CommissionTier(Decimal("100000000"), Decimal("0.001")),   # 1억원까지 0.1%
            CommissionTier(None, Decimal("0.0005"))                   # 1억원 초과 0.05%
        ]
        
        # 거래량별 슬리피지
        self.volume_slippage = {
            TradeSize.SMALL: Decimal("0.0005"),   # 0.05%
            TradeSize.MEDIUM: Decimal("0.001"),   # 0.1%
            TradeSize.LARGE: Decimal("0.002"),    # 0.2%
            TradeSize.HUGE: Decimal("0.005")      # 0.5%
        }
        
        # 시간대별 스프레드
        self.time_spreads = {
            "market_open": Decimal("0.002"),      # 개장 직후 0.2%
            "normal": Decimal("0.001"),           # 정상 시간 0.1%
            "market_close": Decimal("0.0015"),    # 장마감 전 0.15%
            "after_hours": Decimal("0.005")       # 시간외 0.5%
        }
        
        # 시장 상황별 비용 조정 계수
        self.market_multipliers = {
            MarketCondition.BULL: Decimal("0.8"),      # 상승장 20% 절감
            MarketCondition.BEAR: Decimal("1.2"),      # 하락장 20% 증가
            MarketCondition.SIDEWAYS: Decimal("1.0"),  # 횡보장 기본
            MarketCondition.VOLATILE: Decimal("1.5")   # 변동성 장 50% 증가
        }
        
        # 종목별 세율
        self.tax_rates = {
            "stock": Decimal("0.003"),      # 일반 주식 0.3%
            "etf": Decimal("0.0008"),       # ETF 0.08%
            "reit": Decimal("0.0035"),      # 리츠 0.35%
            "bond": Decimal("0.0"),         # 채권 0%
            "derivative": Decimal("0.0")    # 파생상품 0%
        }
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_commission(
        self, 
        notional: Decimal, 
        use_progressive: bool = False
    ) -> Decimal:
        """수수료 계산"""
        try:
            if use_progressive:
                commission = self._calculate_progressive_commission(notional)
            else:
                commission = notional * self.commission_rate
            
            # 최소/최대 수수료 적용
            commission = max(commission, self.min_commission)
            commission = min(commission, self.max_commission)
            
            return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"Commission calculation error: {str(e)}")
            return self.min_commission
    
    def _calculate_progressive_commission(self, notional: Decimal) -> Decimal:
        """누진 수수료 계산"""
        remaining = notional
        total_commission = Decimal("0")
        prev_limit = Decimal("0")
        
        for tier in self.commission_tiers:
            if remaining <= 0:
                break
                
            if tier.limit is None:
                # 마지막 구간
                total_commission += remaining * tier.rate
                break
            else:
                tier_amount = min(remaining, tier.limit - prev_limit)
                if tier_amount > 0:
                    total_commission += tier_amount * tier.rate
                    remaining -= tier_amount
                    prev_limit = tier.limit
        
        return total_commission
    
    def calculate_tax(
        self, 
        notional: Decimal, 
        transaction_type: TransactionType, 
        instrument_type: str = "stock"
    ) -> Decimal:
        """세금 계산"""
        try:
            # 매수시에는 세금 없음
            if transaction_type == TransactionType.BUY:
                return Decimal("0")
            
            # 종목별 세율 적용
            tax_rate = self.tax_rates.get(instrument_type, self.tax_rate)
            tax = notional * tax_rate
            
            return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"Tax calculation error: {str(e)}")
            return Decimal("0")
    
    def calculate_slippage(
        self, 
        price: Decimal, 
        quantity: int, 
        trade_time: Optional[datetime] = None,
        daily_avg_volume: Optional[int] = None
    ) -> Decimal:
        """슬리피지 계산"""
        try:
            # 거래 규모 결정
            trade_size = self._determine_trade_size(quantity, daily_avg_volume)
            
            # 기본 슬리피지율
            base_slippage_rate = self.volume_slippage[trade_size]
            
            # 시간대별 조정
            if trade_time:
                time_multiplier = self._get_time_multiplier(trade_time)
                adjusted_rate = base_slippage_rate * time_multiplier
            else:
                adjusted_rate = base_slippage_rate
            
            # 시장 상황별 조정
            market_multiplier = self.market_multipliers[self.market_condition]
            final_rate = adjusted_rate * market_multiplier
            
            # 슬리피지 계산
            slippage = price * final_rate * quantity
            
            return slippage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"Slippage calculation error: {str(e)}")
            return Decimal("0")
    
    def _determine_trade_size(
        self, 
        quantity: int, 
        daily_avg_volume: Optional[int] = None
    ) -> TradeSize:
        """거래 규모 결정"""
        if daily_avg_volume:
            # 일평균 거래량 대비 비율로 판단
            volume_ratio = quantity / daily_avg_volume
            
            if volume_ratio <= 0.01:        # 1% 이하
                return TradeSize.SMALL
            elif volume_ratio <= 0.05:      # 5% 이하
                return TradeSize.MEDIUM
            elif volume_ratio <= 0.1:       # 10% 이하
                return TradeSize.LARGE
            else:                           # 10% 초과
                return TradeSize.HUGE
        else:
            # 절대 수량으로 판단
            if quantity < 100:
                return TradeSize.SMALL
            elif quantity < 1000:
                return TradeSize.MEDIUM
            elif quantity < 10000:
                return TradeSize.LARGE
            else:
                return TradeSize.HUGE
    
    def _get_time_multiplier(self, trade_time: datetime) -> Decimal:
        """시간대별 조정 계수"""
        hour = trade_time.hour
        minute = trade_time.minute
        
        if hour == 9 and minute < 30:  # 개장 30분
            return Decimal("1.2")       # 20% 증가
        elif hour == 15 and minute >= 15:  # 장마감 15분 전
            return Decimal("1.1")       # 10% 증가
        elif 9 <= hour < 15 or (hour == 15 and minute < 15):  # 정규 장시간
            return Decimal("1.0")       # 기본
        else:  # 시간외
            return Decimal("2.0")       # 100% 증가
    
    def calculate_market_impact(
        self, 
        notional: Decimal, 
        quantity: int, 
        daily_avg_volume: Optional[int] = None
    ) -> Decimal:
        """시장 충격 비용 계산"""
        try:
            if not daily_avg_volume or daily_avg_volume == 0:
                # 기본 시장 충격 (거래 규모 기준)
                trade_size = self._determine_trade_size(quantity)
                impact_rates = {
                    TradeSize.SMALL: Decimal("0.0001"),
                    TradeSize.MEDIUM: Decimal("0.0005"),
                    TradeSize.LARGE: Decimal("0.001"),
                    TradeSize.HUGE: Decimal("0.003")
                }
                impact_rate = impact_rates[trade_size]
            else:
                # 거래량 비율 기반 시장 충격
                volume_ratio = Decimal(str(quantity)) / Decimal(str(daily_avg_volume))
                impact_rate = self._calculate_impact_rate(volume_ratio)
            
            # 시장 상황별 조정
            market_multiplier = self.market_multipliers[self.market_condition]
            adjusted_rate = impact_rate * market_multiplier
            
            market_impact = notional * adjusted_rate
            
            return market_impact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"Market impact calculation error: {str(e)}")
            return Decimal("0")
    
    def _calculate_impact_rate(self, volume_ratio: Decimal) -> Decimal:
        """거래량 비율 기반 시장 충격율 계산"""
        if volume_ratio <= Decimal("0.01"):      # 1% 이하
            return Decimal("0.0001")             # 0.01%
        elif volume_ratio <= Decimal("0.05"):    # 5% 이하
            return volume_ratio * Decimal("0.01") # 비례
        elif volume_ratio <= Decimal("0.1"):     # 10% 이하
            return volume_ratio * Decimal("0.02") # 2배 비례
        else:                                     # 10% 초과
            return volume_ratio * Decimal("0.05") # 5배 비례
    
    def calculate_spread_cost(
        self, 
        notional: Decimal, 
        trade_time: Optional[datetime] = None
    ) -> Decimal:
        """스프레드 비용 계산"""
        try:
            # 시간대별 스프레드
            if trade_time:
                spread_key = self._get_time_period(trade_time)
                spread_rate = self.time_spreads[spread_key]
            else:
                spread_rate = self.time_spreads["normal"]
            
            # 시장 상황별 조정
            market_multiplier = self.market_multipliers[self.market_condition]
            adjusted_rate = spread_rate * market_multiplier
            
            spread_cost = notional * adjusted_rate * Decimal("0.5")  # 스프레드의 절반만 비용
            
            return spread_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"Spread cost calculation error: {str(e)}")
            return Decimal("0")
    
    def _get_time_period(self, trade_time: datetime) -> str:
        """거래 시간대 분류"""
        hour = trade_time.hour
        minute = trade_time.minute
        
        if hour == 9 and minute < 30:  # 개장 30분
            return "market_open"
        elif hour == 15 and minute >= 15:  # 장마감 15분 전
            return "market_close"
        elif 9 <= hour < 15 or (hour == 15 and minute < 15):  # 정규 장시간
            return "normal"
        else:  # 시간외
            return "after_hours"
    
    def calculate_total_cost(
        self,
        price: Decimal,
        quantity: int,
        transaction_type: TransactionType,
        trade_time: Optional[datetime] = None,
        daily_avg_volume: Optional[int] = None,
        instrument_type: str = "stock",
        use_progressive_commission: bool = False
    ) -> CostComponents:
        """총 거래 비용 계산"""
        try:
            notional = price * quantity
            
            # 각 비용 구성 요소 계산
            commission = self.calculate_commission(notional, use_progressive_commission)
            tax = self.calculate_tax(notional, transaction_type, instrument_type)
            slippage = self.calculate_slippage(price, quantity, trade_time, daily_avg_volume)
            spread = self.calculate_spread_cost(notional, trade_time)
            market_impact = self.calculate_market_impact(notional, quantity, daily_avg_volume)
            other_fees = self._calculate_other_fees(notional, instrument_type)
            
            return CostComponents(
                commission=commission,
                tax=tax,
                slippage=slippage,
                spread=spread,
                market_impact=market_impact,
                other_fees=other_fees
            )
            
        except Exception as e:
            self.logger.error(f"Total cost calculation error: {str(e)}")
            return CostComponents(
                commission=self.min_commission,
                tax=Decimal("0"),
                slippage=Decimal("0"),
                spread=Decimal("0"),
                market_impact=Decimal("0"),
                other_fees=Decimal("0")
            )
    
    def _calculate_other_fees(self, notional: Decimal, instrument_type: str) -> Decimal:
        """기타 수수료 계산"""
        # 예: 거래소 수수료, 결제 수수료 등
        other_fee_rates = {
            "stock": Decimal("0.00002"),    # 0.002%
            "etf": Decimal("0.00001"),      # 0.001%
            "reit": Decimal("0.00003"),     # 0.003%
            "bond": Decimal("0.00001"),     # 0.001%
            "derivative": Decimal("0.0001") # 0.01%
        }
        
        fee_rate = other_fee_rates.get(instrument_type, Decimal("0.00002"))
        return (notional * fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def optimize_execution(
        self,
        total_quantity: int,
        price: Decimal,
        transaction_type: TransactionType,
        max_split_count: int = 10
    ) -> Tuple[List[int], Decimal]:
        """실행 최적화 (분할 거래)"""
        try:
            # 한번에 거래시 비용
            single_cost = self.calculate_total_cost(
                price, total_quantity, transaction_type
            ).total_cost
            
            best_split = [total_quantity]
            best_cost = single_cost
            
            # 분할 거래 최적화
            for split_count in range(2, max_split_count + 1):
                if total_quantity % split_count == 0:
                    split_quantity = total_quantity // split_count
                    
                    # 분할 거래 비용
                    split_cost = self.calculate_total_cost(
                        price, split_quantity, transaction_type
                    ).total_cost * split_count
                    
                    if split_cost < best_cost:
                        best_cost = split_cost
                        best_split = [split_quantity] * split_count
            
            return best_split, best_cost
            
        except Exception as e:
            self.logger.error(f"Execution optimization error: {str(e)}")
            return [total_quantity], single_cost
    
    def get_cost_breakdown(
        self,
        price: Decimal,
        quantity: int,
        transaction_type: TransactionType,
        **kwargs
    ) -> Dict[str, any]:
        """비용 분석 리포트 생성"""
        try:
            costs = self.calculate_total_cost(price, quantity, transaction_type, **kwargs)
            notional = price * quantity
            
            breakdown = {
                "notional_value": float(notional),
                "total_cost": float(costs.total_cost),
                "cost_ratio": float(costs.total_cost / notional) if notional > 0 else 0,
                "components": {
                    "commission": {
                        "amount": float(costs.commission),
                        "ratio": float(costs.commission / costs.total_cost) if costs.total_cost > 0 else 0
                    },
                    "tax": {
                        "amount": float(costs.tax),
                        "ratio": float(costs.tax / costs.total_cost) if costs.total_cost > 0 else 0
                    },
                    "slippage": {
                        "amount": float(costs.slippage),
                        "ratio": float(costs.slippage / costs.total_cost) if costs.total_cost > 0 else 0
                    },
                    "spread": {
                        "amount": float(costs.spread),
                        "ratio": float(costs.spread / costs.total_cost) if costs.total_cost > 0 else 0
                    },
                    "market_impact": {
                        "amount": float(costs.market_impact),
                        "ratio": float(costs.market_impact / costs.total_cost) if costs.total_cost > 0 else 0
                    },
                    "other_fees": {
                        "amount": float(costs.other_fees),
                        "ratio": float(costs.other_fees / costs.total_cost) if costs.total_cost > 0 else 0
                    }
                },
                "market_condition": self.market_condition.value,
                "trade_size": self._determine_trade_size(quantity).value
            }
            
            return breakdown
            
        except Exception as e:
            self.logger.error(f"Cost breakdown error: {str(e)}")
            return {
                "error": str(e),
                "notional_value": float(price * quantity),
                "total_cost": float(self.min_commission)
            }
    
    def update_market_condition(self, condition: MarketCondition):
        """시장 상황 업데이트"""
        self.market_condition = condition
        self.logger.info(f"Market condition updated to: {condition.value}")
    
    def get_model_parameters(self) -> Dict[str, any]:
        """모델 파라미터 반환"""
        return {
            "commission_rate": float(self.commission_rate),
            "tax_rate": float(self.tax_rate),
            "slippage_rate": float(self.slippage_rate),
            "min_commission": float(self.min_commission),
            "max_commission": float(self.max_commission),
            "market_condition": self.market_condition.value,
            "commission_tiers": [
                {"limit": float(tier.limit) if tier.limit else None, "rate": float(tier.rate)}
                for tier in self.commission_tiers
            ],
            "volume_slippage": {size.value: float(rate) for size, rate in self.volume_slippage.items()},
            "market_multipliers": {cond.value: float(mult) for cond, mult in self.market_multipliers.items()}
        }