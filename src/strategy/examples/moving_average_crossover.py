# -*- coding: utf-8 -*-
"""
이동평균 크로스오버 전략
"""
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from src.core.interfaces.strategy import Signal, SignalType, MarketData
from src.strategy.base import BaseStrategy, StrategyConfig
from src.strategy.indicators import MovingAverage


class MovingAverageCrossover(BaseStrategy):
    """
    이동평균 크로스오버 전략
    
    단기/장기 이동평균선의 교차를 이용한 추세추종 전략입니다.
    - 골든크로스(단기MA > 장기MA): 매수 신호
    - 데드크로스(단기MA < 장기MA): 매도 신호
    """
    
    def __init__(self, config: StrategyConfig):
        """전략 초기화"""
        super().__init__(config)
        
        # 기본 파라미터 설정
        self.parameter_definitions = {
            "short_period": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 50,
                "description": "단기 이동평균 기간"
            },
            "long_period": {
                "type": "int", 
                "default": 50,
                "min": 20,
                "max": 200,
                "description": "장기 이동평균 기간"
            },
            "ma_type": {
                "type": "str",
                "default": "sma",
                "choices": ["sma", "ema", "wma"],
                "description": "이동평균 타입"
            },
            "position_size": {
                "type": "float",
                "default": 0.95,
                "min": 0.1,
                "max": 1.0,
                "description": "포지션 크기 (자본 대비 비율)"
            },
            "min_signal_strength": {
                "type": "float",
                "default": 0.7,
                "min": 0.1,
                "max": 1.0,
                "description": "최소 신호 강도"
            }
        }
        
        # 전략 상태
        self.price_history: List[float] = []
        self.short_ma_history: List[float] = []
        self.long_ma_history: List[float] = []
        self.current_position: str = "none"  # "long", "short", "none"
        
        # 지표 초기화
        self.short_ma_indicator = None
        self.long_ma_indicator = None
        
        # 성과 추적
        self.last_crossover_date: datetime = None
        self.crossover_count = 0
        self.false_signals = 0
    
    @property
    def description(self) -> str:
        """전략 설명"""
        return (
            "단기/장기 이동평균선의 교차를 이용한 추세추종 전략입니다. "
            "골든크로스 시 매수, 데드크로스 시 매도 신호를 생성합니다."
        )
    
    async def on_initialize(self):
        """커스텀 초기화"""
        params = self.parameters
        
        # 이동평균 지표 생성
        ma_type = params.get("ma_type", "sma")
        short_period = params.get("short_period", 20)
        long_period = params.get("long_period", 50)
        
        self.short_ma_indicator = MovingAverage(short_period, ma_type)
        self.long_ma_indicator = MovingAverage(long_period, ma_type)
        
        self.logger.info(
            f"Initialized MA Crossover: {short_period}-{ma_type.upper()} x "
            f"{long_period}-{ma_type.upper()}"
        )
    
    async def generate_signals(self, data: MarketData) -> List[Signal]:
        """신호 생성"""
        signals = []
        
        # 가격 히스토리 업데이트
        self.price_history.append(data.close)
        
        # 충분한 데이터가 있는지 확인
        long_period = self.parameters.get("long_period", 50)
        if len(self.price_history) < long_period + 1:
            return signals
        
        # 이동평균 계산
        import pandas as pd
        df = pd.DataFrame({"close": self.price_history})
        
        short_ma_values = self.short_ma_indicator.calculate(df)
        long_ma_values = self.long_ma_indicator.calculate(df)
        
        # 현재와 이전 이동평균 값
        current_short_ma = short_ma_values.iloc[-1] if not short_ma_values.empty else None
        current_long_ma = long_ma_values.iloc[-1] if not long_ma_values.empty else None
        
        if current_short_ma is None or current_long_ma is None:
            return signals
        
        # 이전 값 (크로스오버 감지용)
        prev_short_ma = short_ma_values.iloc[-2] if len(short_ma_values) >= 2 else None
        prev_long_ma = long_ma_values.iloc[-2] if len(long_ma_values) >= 2 else None
        
        if prev_short_ma is None or prev_long_ma is None:
            return signals
        
        # 히스토리 업데이트
        self.short_ma_history.append(current_short_ma)
        self.long_ma_history.append(current_long_ma)
        
        # 크로스오버 감지
        signal = self._detect_crossover(
            data, 
            current_short_ma, current_long_ma,
            prev_short_ma, prev_long_ma
        )
        
        if signal:
            signals.append(signal)
            self.crossover_count += 1
            self.last_crossover_date = data.timestamp
        
        return signals
    
    def _detect_crossover(
        self,
        data: MarketData,
        current_short_ma: float,
        current_long_ma: float, 
        prev_short_ma: float,
        prev_long_ma: float
    ) -> Signal:
        """크로스오버 감지"""
        
        # 골든 크로스 (매수 신호)
        if (prev_short_ma <= prev_long_ma and 
            current_short_ma > current_long_ma and
            self.current_position != "long"):
            
            # 신호 강도 계산
            ma_diff_ratio = (current_short_ma - current_long_ma) / current_long_ma
            price_position = (data.close - current_long_ma) / current_long_ma
            strength = min(1.0, (abs(ma_diff_ratio) + abs(price_position)) * 2)
            
            # 최소 신호 강도 확인
            min_strength = self.parameters.get("min_signal_strength", 0.7)
            if strength < min_strength:
                self.false_signals += 1
                return None
            
            self.current_position = "long"
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                price=data.close,
                reason=f"Golden Cross (MA{self.parameters.get('short_period')}/{self.parameters.get('long_period')})",
                metadata={
                    "short_ma": current_short_ma,
                    "long_ma": current_long_ma,
                    "ma_diff_ratio": ma_diff_ratio,
                    "price_position": price_position
                }
            )
        
        # 데드 크로스 (매도 신호)
        elif (prev_short_ma >= prev_long_ma and 
              current_short_ma < current_long_ma and
              self.current_position == "long"):
            
            # 신호 강도 계산
            ma_diff_ratio = (current_long_ma - current_short_ma) / current_long_ma
            price_position = (current_long_ma - data.close) / current_long_ma
            strength = min(1.0, (abs(ma_diff_ratio) + abs(price_position)) * 2)
            
            # 최소 신호 강도 확인
            min_strength = self.parameters.get("min_signal_strength", 0.7)
            if strength < min_strength:
                self.false_signals += 1
                return None
            
            self.current_position = "none"
            
            return Signal(
                timestamp=data.timestamp,
                symbol=data.symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                price=data.close,
                reason=f"Death Cross (MA{self.parameters.get('short_period')}/{self.parameters.get('long_period')})",
                metadata={
                    "short_ma": current_short_ma,
                    "long_ma": current_long_ma,
                    "ma_diff_ratio": ma_diff_ratio,
                    "price_position": price_position
                }
            )
        
        return None
    
    def validate_custom_parameters(self) -> bool:
        """커스텀 파라미터 검증"""
        params = self.parameters
        
        short_period = params.get("short_period", 20)
        long_period = params.get("long_period", 50)
        
        if short_period >= long_period:
            self.logger.error("Short period must be less than long period")
            return False
        
        ma_type = params.get("ma_type", "sma")
        if ma_type not in ["sma", "ema", "wma"]:
            self.logger.error("Invalid MA type. Must be 'sma', 'ema', or 'wma'")
            return False
        
        position_size = params.get("position_size", 0.95)
        if not 0.1 <= position_size <= 1.0:
            self.logger.error("Position size must be between 0.1 and 1.0")
            return False
        
        return True
    
    def validate_signal(self, signal: Signal) -> bool:
        """커스텀 신호 검증"""
        # 너무 자주 신호가 발생하는지 확인
        if (self.last_crossover_date and 
            signal.timestamp and
            (signal.timestamp - self.last_crossover_date).days < 3):
            return False
        
        # 메타데이터 확인
        if not signal.metadata or "short_ma" not in signal.metadata:
            return False
        
        return True
    
    async def on_order_execution(self, order: Any):
        """주문 체결 후 처리"""
        if hasattr(order, 'side'):
            if order.side == "buy":
                self.logger.info(f"Long position opened at {order.price}")
            elif order.side == "sell":
                self.logger.info(f"Position closed at {order.price}")
    
    async def on_daily_close(self):
        """일일 마감 처리"""
        if len(self.price_history) > 0:
            current_price = self.price_history[-1]
            
            if len(self.short_ma_history) > 0 and len(self.long_ma_history) > 0:
                short_ma = self.short_ma_history[-1]
                long_ma = self.long_ma_history[-1]
                
                trend = "상승" if short_ma > long_ma else "하락"
                
                self.logger.debug(
                    f"Daily summary - Price: {current_price:.2f}, "
                    f"Short MA: {short_ma:.2f}, Long MA: {long_ma:.2f}, "
                    f"Trend: {trend}, Position: {self.current_position}"
                )
    
    def get_strategy_specific_stats(self) -> Dict[str, Any]:
        """전략별 통계"""
        return {
            "crossover_count": self.crossover_count,
            "false_signals": self.false_signals,
            "current_position": self.current_position,
            "last_crossover": self.last_crossover_date.isoformat() if self.last_crossover_date else None,
            "data_points": len(self.price_history),
            "short_ma_current": self.short_ma_history[-1] if self.short_ma_history else None,
            "long_ma_current": self.long_ma_history[-1] if self.long_ma_history else None,
            "trend": "bullish" if (self.short_ma_history and self.long_ma_history and 
                                 self.short_ma_history[-1] > self.long_ma_history[-1]) else "bearish"
        }