# -*- coding: utf-8 -*-
"""
RSI 전략
"""
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from src.core.interfaces.strategy import Signal, SignalType, MarketData
from src.strategy.base import BaseStrategy, StrategyConfig
from src.strategy.indicators import RSI


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) 전략
    
    RSI 지표를 이용한 과매수/과매도 영역에서의 역추세 전략입니다.
    - RSI < 30: 과매도 → 매수 신호
    - RSI > 70: 과매수 → 매도 신호
    """
    
    def __init__(self, config: StrategyConfig):
        """전략 초기화"""
        super().__init__(config)
        
        # 기본 파라미터 설정
        self.parameter_definitions = {
            "rsi_period": {
                "type": "int",
                "default": 14,
                "min": 5,
                "max": 30,
                "description": "RSI 계산 기간"
            },
            "oversold_threshold": {
                "type": "float",
                "default": 30.0,
                "min": 10.0,
                "max": 40.0,
                "description": "과매도 임계값"
            },
            "overbought_threshold": {
                "type": "float",
                "default": 70.0,
                "min": 60.0,
                "max": 90.0,
                "description": "과매수 임계값"
            },
            "extreme_oversold": {
                "type": "float",
                "default": 20.0,
                "min": 5.0,
                "max": 25.0,
                "description": "극과매도 임계값 (강한 매수 신호)"
            },
            "extreme_overbought": {
                "type": "float",
                "default": 80.0,
                "min": 75.0,
                "max": 95.0,
                "description": "극과매수 임계값 (강한 매도 신호)"
            },
            "position_size": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "description": "포지션 크기 (자본 대비 비율)"
            },
            "min_hold_days": {
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 10,
                "description": "최소 보유 기간 (일)"
            }
        }
        
        # 전략 상태
        self.price_history: List[float] = []
        self.rsi_history: List[float] = []
        self.current_position: str = "none"  # "long", "short", "none"
        self.position_entry_date: datetime = None
        
        # 지표 초기화
        self.rsi_indicator = None
        
        # 성과 추적
        self.oversold_signals = 0
        self.overbought_signals = 0
        self.extreme_signals = 0
        self.whipsaw_count = 0  # 짧은 기간 반복 거래
        
    @property
    def description(self) -> str:
        """전략 설명"""
        return (
            "RSI 지표를 이용한 과매수/과매도 역추세 전략입니다. "
            "과매도 구간에서 매수, 과매수 구간에서 매도 신호를 생성합니다."
        )
    
    async def on_initialize(self):
        """커스텀 초기화"""
        params = self.parameters
        
        # RSI 지표 생성
        rsi_period = params.get("rsi_period", 14)
        self.rsi_indicator = RSI(rsi_period)
        
        self.logger.info(f"Initialized RSI Strategy: period={rsi_period}")
    
    async def generate_signals(self, data: MarketData) -> List[Signal]:
        """신호 생성"""
        signals = []
        
        # 가격 히스토리 업데이트
        self.price_history.append(data.close)
        
        # 충분한 데이터가 있는지 확인
        rsi_period = self.parameters.get("rsi_period", 14)
        if len(self.price_history) < rsi_period + 1:
            return signals
        
        # RSI 계산
        import pandas as pd
        df = pd.DataFrame({"close": self.price_history})
        
        rsi_values = self.rsi_indicator.calculate(df)
        current_rsi = rsi_values.iloc[-1] if not rsi_values.empty else None
        
        if current_rsi is None or np.isnan(current_rsi):
            return signals
        
        # RSI 히스토리 업데이트
        self.rsi_history.append(current_rsi)
        
        # 신호 생성
        signal = self._generate_rsi_signal(data, current_rsi)
        
        if signal:
            signals.append(signal)
        
        return signals
    
    def _generate_rsi_signal(self, data: MarketData, current_rsi: float) -> Signal:
        """RSI 기반 신호 생성"""
        params = self.parameters
        
        oversold = params.get("oversold_threshold", 30.0)
        overbought = params.get("overbought_threshold", 70.0)
        extreme_oversold = params.get("extreme_oversold", 20.0)
        extreme_overbought = params.get("extreme_overbought", 80.0)
        min_hold_days = params.get("min_hold_days", 3)
        
        # 최소 보유 기간 확인
        if (self.position_entry_date and 
            (data.timestamp - self.position_entry_date).days < min_hold_days):
            return None
        
        # 과매도 구간 (매수 신호)
        if current_rsi <= oversold and self.current_position != "long":
            
            # 신호 강도 계산
            if current_rsi <= extreme_oversold:
                strength = 1.0
                reason = f"Extreme Oversold (RSI: {current_rsi:.1f})"
                self.extreme_signals += 1
            else:
                strength = (oversold - current_rsi) / oversold
                reason = f"Oversold (RSI: {current_rsi:.1f})"
                self.oversold_signals += 1
            
            # 추가 확인: RSI 바닥 형성 확인
            if len(self.rsi_history) >= 3:
                prev_rsi = self.rsi_history[-2]
                if current_rsi > prev_rsi:  # RSI 상승 전환
                    strength *= 1.2  # 신호 강도 증가
                    reason += " + RSI Reversal"
            
            self._update_position("long", data.timestamp)
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=min(1.0, strength),
                price=data.close,
                reason=reason,
                metadata={
                    "rsi": current_rsi,
                    "oversold_threshold": oversold,
                    "extreme_oversold": extreme_oversold,
                    "signal_type": "oversold_buy"
                }
            )
        
        # 과매수 구간 (매도 신호)
        elif current_rsi >= overbought and self.current_position == "long":
            
            # 신호 강도 계산
            if current_rsi >= extreme_overbought:
                strength = 1.0
                reason = f"Extreme Overbought (RSI: {current_rsi:.1f})"
                self.extreme_signals += 1
            else:
                strength = (current_rsi - overbought) / (100 - overbought)
                reason = f"Overbought (RSI: {current_rsi:.1f})"
                self.overbought_signals += 1
            
            # 추가 확인: RSI 고점 형성 확인
            if len(self.rsi_history) >= 3:
                prev_rsi = self.rsi_history[-2]
                if current_rsi < prev_rsi:  # RSI 하락 전환
                    strength *= 1.2  # 신호 강도 증가
                    reason += " + RSI Reversal"
            
            # 보유 기간이 너무 짧으면 휩소우 카운트
            if (self.position_entry_date and 
                (data.timestamp - self.position_entry_date).days <= 2):
                self.whipsaw_count += 1
            
            self._update_position("none", data.timestamp)
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.SELL,
                strength=min(1.0, strength),
                price=data.close,
                reason=reason,
                metadata={
                    "rsi": current_rsi,
                    "overbought_threshold": overbought,
                    "extreme_overbought": extreme_overbought,
                    "signal_type": "overbought_sell",
                    "hold_days": (data.timestamp - self.position_entry_date).days if self.position_entry_date else 0
                }
            )
        
        # RSI 다이버전스 확인 (고급 신호)
        divergence_signal = self._check_divergence(data, current_rsi)
        if divergence_signal:
            return divergence_signal
        
        return None
    
    def _check_divergence(self, data: MarketData, current_rsi: float) -> Signal:
        """RSI 다이버전스 확인"""
        # 최소 20개 데이터 포인트 필요
        if len(self.price_history) < 20 or len(self.rsi_history) < 20:
            return None
        
        # 최근 10일간의 데이터로 다이버전스 확인
        recent_prices = self.price_history[-10:]
        recent_rsi = self.rsi_history[-10:]
        
        # 가격 고점/저점과 RSI 고점/저점 비교
        price_high_idx = np.argmax(recent_prices)
        price_low_idx = np.argmin(recent_prices)
        rsi_high_idx = np.argmax(recent_rsi)
        rsi_low_idx = np.argmin(recent_rsi)
        
        # 약세 다이버전스 (가격 상승, RSI 하락)
        if (price_high_idx > rsi_high_idx and 
            recent_prices[price_high_idx] > recent_prices[rsi_high_idx] and
            recent_rsi[price_high_idx] < recent_rsi[rsi_high_idx] and
            self.current_position == "long"):
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.SELL,
                strength=0.8,
                price=data.close,
                reason=f"Bearish Divergence (RSI: {current_rsi:.1f})",
                metadata={
                    "rsi": current_rsi,
                    "signal_type": "bearish_divergence",
                    "divergence_strength": abs(recent_rsi[rsi_high_idx] - recent_rsi[price_high_idx])
                }
            )
        
        # 강세 다이버전스 (가격 하락, RSI 상승)
        elif (price_low_idx > rsi_low_idx and 
              recent_prices[price_low_idx] < recent_prices[rsi_low_idx] and
              recent_rsi[price_low_idx] > recent_rsi[rsi_low_idx] and
              self.current_position != "long"):
            
            self._update_position("long", data.timestamp)
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=0.8,
                price=data.close,
                reason=f"Bullish Divergence (RSI: {current_rsi:.1f})",
                metadata={
                    "rsi": current_rsi,
                    "signal_type": "bullish_divergence",
                    "divergence_strength": abs(recent_rsi[rsi_low_idx] - recent_rsi[price_low_idx])
                }
            )
        
        return None
    
    def _update_position(self, position: str, timestamp: datetime):
        """포지션 상태 업데이트"""
        if position != self.current_position:
            self.current_position = position
            if position == "long":
                self.position_entry_date = timestamp
            else:
                self.position_entry_date = None
    
    def validate_custom_parameters(self) -> bool:
        """커스텀 파라미터 검증"""
        params = self.parameters
        
        oversold = params.get("oversold_threshold", 30.0)
        overbought = params.get("overbought_threshold", 70.0)
        extreme_oversold = params.get("extreme_oversold", 20.0)
        extreme_overbought = params.get("extreme_overbought", 80.0)
        
        if oversold >= overbought:
            self.logger.error("Oversold threshold must be less than overbought threshold")
            return False
        
        if extreme_oversold >= oversold:
            self.logger.error("Extreme oversold must be less than oversold threshold")
            return False
        
        if extreme_overbought <= overbought:
            self.logger.error("Extreme overbought must be greater than overbought threshold")
            return False
        
        rsi_period = params.get("rsi_period", 14)
        if rsi_period < 5 or rsi_period > 30:
            self.logger.error("RSI period must be between 5 and 30")
            return False
        
        return True
    
    def validate_signal(self, signal: Signal) -> bool:
        """커스텀 신호 검증"""
        # RSI 값이 유효 범위인지 확인
        if signal.metadata and "rsi" in signal.metadata:
            rsi_value = signal.metadata["rsi"]
            if not 0 <= rsi_value <= 100:
                return False
        
        return True
    
    async def on_order_execution(self, order: Any):
        """주문 체결 후 처리"""
        if hasattr(order, 'side'):
            current_rsi = self.rsi_history[-1] if self.rsi_history else "N/A"
            
            if order.side == "buy":
                self.logger.info(f"Long position opened at {order.price} (RSI: {current_rsi})")
            elif order.side == "sell":
                hold_days = 0
                if self.position_entry_date:
                    hold_days = (datetime.now() - self.position_entry_date).days
                self.logger.info(f"Position closed at {order.price} (RSI: {current_rsi}, Hold: {hold_days}d)")
    
    async def on_daily_close(self):
        """일일 마감 처리"""
        if len(self.rsi_history) > 0:
            current_rsi = self.rsi_history[-1]
            
            # RSI 상태 분류
            if current_rsi <= 30:
                rsi_status = "과매도"
            elif current_rsi >= 70:
                rsi_status = "과매수"
            else:
                rsi_status = "중립"
            
            hold_days = 0
            if self.position_entry_date:
                hold_days = (datetime.now() - self.position_entry_date).days
            
            self.logger.debug(
                f"Daily RSI: {current_rsi:.1f} ({rsi_status}), "
                f"Position: {self.current_position}, Hold: {hold_days}d"
            )
    
    def get_strategy_specific_stats(self) -> Dict[str, Any]:
        """전략별 통계"""
        return {
            "oversold_signals": self.oversold_signals,
            "overbought_signals": self.overbought_signals,
            "extreme_signals": self.extreme_signals,
            "whipsaw_count": self.whipsaw_count,
            "current_position": self.current_position,
            "position_entry_date": self.position_entry_date.isoformat() if self.position_entry_date else None,
            "current_rsi": self.rsi_history[-1] if self.rsi_history else None,
            "avg_rsi": np.mean(self.rsi_history) if self.rsi_history else None,
            "rsi_volatility": np.std(self.rsi_history) if self.rsi_history else None,
            "data_points": len(self.price_history)
        }