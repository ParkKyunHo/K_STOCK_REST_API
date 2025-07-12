# -*- coding: utf-8 -*-
"""
볼린저 밴드 전략
"""
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from src.core.interfaces.strategy import Signal, SignalType, MarketData
from src.strategy.base import BaseStrategy, StrategyConfig
from src.strategy.indicators import BollingerBands, RSI


class BollingerBandsStrategy(BaseStrategy):
    """
    볼린저 밴드 전략
    
    볼린저 밴드의 상/하단 돌파와 %B 지표를 이용한 변동성 전략입니다.
    - 하단 밴드 터치 + %B < 0.2: 매수 신호
    - 상단 밴드 터치 + %B > 0.8: 매도 신호
    - RSI와 조합하여 신호 필터링
    """
    
    def __init__(self, config: StrategyConfig):
        """전략 초기화"""
        super().__init__(config)
        
        # 기본 파라미터 설정
        self.parameter_definitions = {
            "bb_period": {
                "type": "int",
                "default": 20,
                "min": 10,
                "max": 50,
                "description": "볼린저 밴드 기간"
            },
            "bb_std": {
                "type": "float",
                "default": 2.0,
                "min": 1.0,
                "max": 3.0,
                "description": "볼린저 밴드 표준편차 배수"
            },
            "buy_threshold": {
                "type": "float",
                "default": 0.2,
                "min": 0.0,
                "max": 0.5,
                "description": "매수 %B 임계값"
            },
            "sell_threshold": {
                "type": "float",
                "default": 0.8,
                "min": 0.5,
                "max": 1.0,
                "description": "매도 %B 임계값"
            },
            "use_rsi_filter": {
                "type": "bool",
                "default": True,
                "description": "RSI 필터 사용 여부"
            },
            "rsi_period": {
                "type": "int",
                "default": 14,
                "min": 5,
                "max": 30,
                "description": "RSI 기간 (필터용)"
            },
            "rsi_oversold": {
                "type": "float",
                "default": 35.0,
                "min": 20.0,
                "max": 45.0,
                "description": "RSI 과매도 임계값"
            },
            "rsi_overbought": {
                "type": "float",
                "default": 65.0,
                "min": 55.0,
                "max": 80.0,
                "description": "RSI 과매수 임계값"
            },
            "bandwidth_threshold": {
                "type": "float",
                "default": 0.1,
                "min": 0.05,
                "max": 0.3,
                "description": "밴드폭 임계값 (변동성 필터)"
            },
            "position_size": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "description": "포지션 크기 (자본 대비 비율)"
            }
        }
        
        # 전략 상태
        self.price_history: List[float] = []
        self.bb_history: List[Dict[str, float]] = []
        self.rsi_history: List[float] = []
        self.current_position: str = "none"  # "long", "short", "none"
        self.position_entry_date: datetime = None
        self.position_entry_price: float = None
        
        # 지표 초기화
        self.bb_indicator = None
        self.rsi_indicator = None
        
        # 성과 추적
        self.bb_breakout_signals = 0
        self.bb_reversal_signals = 0
        self.squeeze_breakouts = 0
        self.false_breakouts = 0
        
    @property
    def description(self) -> str:
        """전략 설명"""
        return (
            "볼린저 밴드의 상/하단 돌파와 %B 지표를 이용한 변동성 전략입니다. "
            "밴드 터치 시점에서 반전 매매와 스퀴즈 후 돌파 매매를 결합합니다."
        )
    
    async def on_initialize(self):
        """커스텀 초기화"""
        params = self.parameters
        
        # 볼린저 밴드 지표 생성
        bb_period = params.get("bb_period", 20)
        bb_std = params.get("bb_std", 2.0)
        self.bb_indicator = BollingerBands(bb_period, bb_std)
        
        # RSI 지표 생성 (필터용)
        if params.get("use_rsi_filter", True):
            rsi_period = params.get("rsi_period", 14)
            self.rsi_indicator = RSI(rsi_period)
        
        self.logger.info(
            f"Initialized Bollinger Bands Strategy: period={bb_period}, std={bb_std}"
        )
    
    async def generate_signals(self, data: MarketData) -> List[Signal]:
        """신호 생성"""
        signals = []
        
        # 가격 히스토리 업데이트
        self.price_history.append(data.close)
        
        # 충분한 데이터가 있는지 확인
        bb_period = self.parameters.get("bb_period", 20)
        if len(self.price_history) < bb_period + 1:
            return signals
        
        # 볼린저 밴드 계산
        import pandas as pd
        df = pd.DataFrame({"close": self.price_history, "high": [data.high] * len(self.price_history), "low": [data.low] * len(self.price_history)})
        
        bb_data = self.bb_indicator.calculate(df)
        
        if bb_data.empty:
            return signals
        
        # 현재 볼린저 밴드 값
        current_bb = {
            "upper": bb_data["bb_upper"].iloc[-1],
            "middle": bb_data["bb_middle"].iloc[-1],
            "lower": bb_data["bb_lower"].iloc[-1],
            "percent_b": bb_data["bb_percent"].iloc[-1],
            "width": bb_data["bb_width"].iloc[-1]
        }
        
        # RSI 계산 (필터용)
        current_rsi = None
        if self.rsi_indicator:
            rsi_values = self.rsi_indicator.calculate(df)
            if not rsi_values.empty:
                current_rsi = rsi_values.iloc[-1]
                self.rsi_history.append(current_rsi)
        
        # 볼린저 밴드 히스토리 업데이트
        self.bb_history.append(current_bb)
        
        # 신호 생성
        signal = self._generate_bb_signal(data, current_bb, current_rsi)
        
        if signal:
            signals.append(signal)
        
        return signals
    
    def _generate_bb_signal(
        self, 
        data: MarketData, 
        bb_data: Dict[str, float], 
        rsi: float = None
    ) -> Signal:
        """볼린저 밴드 기반 신호 생성"""
        
        params = self.parameters
        buy_threshold = params.get("buy_threshold", 0.2)
        sell_threshold = params.get("sell_threshold", 0.8)
        bandwidth_threshold = params.get("bandwidth_threshold", 0.1)
        use_rsi_filter = params.get("use_rsi_filter", True)
        
        current_price = data.close
        percent_b = bb_data["percent_b"]
        bandwidth = bb_data["width"]
        
        # 변동성 필터 (밴드폭이 너무 좁으면 신호 생성 안함)
        if bandwidth < bandwidth_threshold:
            return None
        
        # 스퀴즈 후 돌파 확인
        squeeze_signal = self._check_squeeze_breakout(data, bb_data)
        if squeeze_signal:
            return squeeze_signal
        
        # 밴드 터치 반전 신호
        reversal_signal = self._check_band_reversal(data, bb_data, rsi, use_rsi_filter)
        if reversal_signal:
            return reversal_signal
        
        return None
    
    def _check_squeeze_breakout(self, data: MarketData, bb_data: Dict[str, float]) -> Signal:
        """스퀴즈 후 돌파 확인"""
        if len(self.bb_history) < 10:
            return None
        
        # 최근 10일간 밴드폭 확인
        recent_widths = [bb["width"] for bb in self.bb_history[-10:]]
        avg_width = np.mean(recent_widths)
        current_width = bb_data["width"]
        
        # 스퀴즈 상태 확인 (밴드폭이 평균보다 50% 이상 감소)
        if current_width > avg_width * 0.5:
            return None
        
        # 돌파 확인
        current_price = data.close
        upper_band = bb_data["upper"]
        lower_band = bb_data["lower"]
        
        # 상단 돌파 (매수 신호 - 추세 추종)
        if (current_price > upper_band and 
            self.current_position != "long"):
            
            strength = min(1.0, (current_price - upper_band) / upper_band * 10)
            
            self._update_position("long", data.timestamp, data.close)
            self.squeeze_breakouts += 1
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                price=data.close,
                reason=f"Squeeze Breakout (Width: {current_width:.3f})",
                metadata={
                    "signal_type": "squeeze_breakout",
                    "percent_b": bb_data["percent_b"],
                    "bandwidth": current_width,
                    "avg_bandwidth": avg_width,
                    **bb_data
                }
            )
        
        # 하단 돌파 확인 (매도 신호 - 현재는 롱 포지션 청산만)
        elif (current_price < lower_band and 
              self.current_position == "long"):
            
            strength = min(1.0, (lower_band - current_price) / lower_band * 10)
            
            self._update_position("none", data.timestamp, data.close)
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                price=data.close,
                reason=f"Squeeze Breakdown (Width: {current_width:.3f})",
                metadata={
                    "signal_type": "squeeze_breakdown",
                    "percent_b": bb_data["percent_b"],
                    "bandwidth": current_width,
                    **bb_data
                }
            )
        
        return None
    
    def _check_band_reversal(
        self, 
        data: MarketData, 
        bb_data: Dict[str, float], 
        rsi: float,
        use_rsi_filter: bool
    ) -> Signal:
        """밴드 터치 반전 신호 확인"""
        
        params = self.parameters
        buy_threshold = params.get("buy_threshold", 0.2)
        sell_threshold = params.get("sell_threshold", 0.8)
        rsi_oversold = params.get("rsi_oversold", 35.0)
        rsi_overbought = params.get("rsi_overbought", 65.0)
        
        percent_b = bb_data["percent_b"]
        current_price = data.close
        
        # 하단 밴드 근처에서 매수 신호
        if (percent_b <= buy_threshold and 
            self.current_position != "long"):
            
            # RSI 필터 적용
            if use_rsi_filter and rsi is not None:
                if rsi > rsi_oversold:
                    return None
            
            # 신호 강도 계산
            strength = 1.0 - percent_b  # %B가 낮을수록 강한 신호
            
            # RSI 추가 확인
            if rsi is not None and rsi < 30:
                strength *= 1.2  # 극과매도 시 신호 강화
            
            # 가격이 실제로 하단 밴드에 근접했는지 확인
            lower_distance = abs(current_price - bb_data["lower"]) / bb_data["lower"]
            if lower_distance > 0.02:  # 2% 이상 떨어져 있으면 패스
                return None
            
            self._update_position("long", data.timestamp, data.close)
            self.bb_reversal_signals += 1
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=min(1.0, strength),
                price=data.close,
                reason=f"BB Lower Reversal (%B: {percent_b:.3f}, RSI: {rsi:.1f})",
                metadata={
                    "signal_type": "bb_reversal_buy",
                    "percent_b": percent_b,
                    "rsi": rsi,
                    "lower_distance": lower_distance,
                    **bb_data
                }
            )
        
        # 상단 밴드 근처에서 매도 신호
        elif (percent_b >= sell_threshold and 
              self.current_position == "long"):
            
            # RSI 필터 적용
            if use_rsi_filter and rsi is not None:
                if rsi < rsi_overbought:
                    return None
            
            # 신호 강도 계산
            strength = percent_b  # %B가 높을수록 강한 신호
            
            # RSI 추가 확인
            if rsi is not None and rsi > 70:
                strength *= 1.2  # 극과매수 시 신호 강화
            
            # 가격이 실제로 상단 밴드에 근접했는지 확인
            upper_distance = abs(current_price - bb_data["upper"]) / bb_data["upper"]
            if upper_distance > 0.02:  # 2% 이상 떨어져 있으면 패스
                return None
            
            # 수익 확인 (손실 중이면 신호 약화)
            profit_ratio = 0
            if self.position_entry_price:
                profit_ratio = (current_price - self.position_entry_price) / self.position_entry_price
                if profit_ratio < 0:
                    strength *= 0.7  # 손실 중이면 신호 약화
            
            self._update_position("none", data.timestamp, data.close)
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.SELL,
                strength=min(1.0, strength),
                price=data.close,
                reason=f"BB Upper Reversal (%B: {percent_b:.3f}, RSI: {rsi:.1f})",
                metadata={
                    "signal_type": "bb_reversal_sell",
                    "percent_b": percent_b,
                    "rsi": rsi,
                    "upper_distance": upper_distance,
                    "profit_ratio": profit_ratio,
                    **bb_data
                }
            )
        
        return None
    
    def _update_position(self, position: str, timestamp: datetime, price: float):
        """포지션 상태 업데이트"""
        if position != self.current_position:
            self.current_position = position
            if position == "long":
                self.position_entry_date = timestamp
                self.position_entry_price = price
            else:
                self.position_entry_date = None
                self.position_entry_price = None
    
    def validate_custom_parameters(self) -> bool:
        """커스텀 파라미터 검증"""
        params = self.parameters
        
        buy_threshold = params.get("buy_threshold", 0.2)
        sell_threshold = params.get("sell_threshold", 0.8)
        
        if buy_threshold >= sell_threshold:
            self.logger.error("Buy threshold must be less than sell threshold")
            return False
        
        bb_std = params.get("bb_std", 2.0)
        if bb_std < 1.0 or bb_std > 3.0:
            self.logger.error("Bollinger Bands standard deviation must be between 1.0 and 3.0")
            return False
        
        if params.get("use_rsi_filter", True):
            rsi_oversold = params.get("rsi_oversold", 35.0)
            rsi_overbought = params.get("rsi_overbought", 65.0)
            
            if rsi_oversold >= rsi_overbought:
                self.logger.error("RSI oversold must be less than overbought")
                return False
        
        return True
    
    def validate_signal(self, signal: Signal) -> bool:
        """커스텀 신호 검증"""
        # %B 값이 유효 범위인지 확인
        if signal.metadata and "percent_b" in signal.metadata:
            percent_b = signal.metadata["percent_b"]
            if percent_b < -0.5 or percent_b > 1.5:  # 일반적 범위를 벗어나면 무효
                return False
        
        return True
    
    async def on_order_execution(self, order: Any):
        """주문 체결 후 처리"""
        if hasattr(order, 'side'):
            current_bb = self.bb_history[-1] if self.bb_history else {}
            percent_b = current_bb.get("percent_b", "N/A")
            rsi = self.rsi_history[-1] if self.rsi_history else "N/A"
            
            if order.side == "buy":
                self.logger.info(
                    f"Long position opened at {order.price} "
                    f"(%B: {percent_b}, RSI: {rsi})"
                )
            elif order.side == "sell":
                profit = 0
                if self.position_entry_price:
                    profit = (order.price - self.position_entry_price) / self.position_entry_price * 100
                
                self.logger.info(
                    f"Position closed at {order.price} "
                    f"(%B: {percent_b}, RSI: {rsi}, P&L: {profit:.2f}%)"
                )
    
    async def on_daily_close(self):
        """일일 마감 처리"""
        if len(self.bb_history) > 0 and len(self.price_history) > 0:
            current_bb = self.bb_history[-1]
            current_price = self.price_history[-1]
            
            percent_b = current_bb["percent_b"]
            bandwidth = current_bb["width"]
            
            # 밴드 위치 분류
            if percent_b < 0.2:
                position_status = "하단 근처"
            elif percent_b > 0.8:
                position_status = "상단 근처"
            else:
                position_status = "중간 영역"
            
            # 변동성 상태
            volatility_status = "높음" if bandwidth > 0.15 else "낮음" if bandwidth < 0.05 else "보통"
            
            self.logger.debug(
                f"Daily BB: %B={percent_b:.3f} ({position_status}), "
                f"Width={bandwidth:.3f} ({volatility_status}), "
                f"Position: {self.current_position}"
            )
    
    def get_strategy_specific_stats(self) -> Dict[str, Any]:
        """전략별 통계"""
        recent_bb = self.bb_history[-1] if self.bb_history else {}
        
        return {
            "bb_breakout_signals": self.bb_breakout_signals,
            "bb_reversal_signals": self.bb_reversal_signals,
            "squeeze_breakouts": self.squeeze_breakouts,
            "false_breakouts": self.false_breakouts,
            "current_position": self.current_position,
            "position_entry_date": self.position_entry_date.isoformat() if self.position_entry_date else None,
            "position_entry_price": self.position_entry_price,
            "current_percent_b": recent_bb.get("percent_b"),
            "current_bandwidth": recent_bb.get("width"),
            "avg_bandwidth": np.mean([bb["width"] for bb in self.bb_history]) if self.bb_history else None,
            "current_rsi": self.rsi_history[-1] if self.rsi_history else None,
            "data_points": len(self.price_history)
        }