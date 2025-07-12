# -*- coding: utf-8 -*-
"""
기술적 지표 라이브러리
"""
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Union, Optional, Dict, Any


class IIndicator(ABC):
    """지표 인터페이스"""
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> Union[pd.Series, pd.DataFrame]:
        """
        지표 계산
        
        Args:
            data: OHLCV 데이터프레임
            
        Returns:
            계산된 지표 값
        """
        pass
    
    @property
    @abstractmethod
    def required_periods(self) -> int:
        """필요한 최소 데이터 기간"""
        pass
    
    def is_ready(self, data: pd.DataFrame) -> bool:
        """지표 계산 준비 상태 확인"""
        return len(data) >= self.required_periods


class MovingAverage(IIndicator):
    """이동평균"""
    
    def __init__(self, period: int = 20, ma_type: str = "sma"):
        """
        이동평균 초기화
        
        Args:
            period: 이동평균 기간
            ma_type: 이동평균 타입 ('sma', 'ema', 'wma')
        """
        self.period = period
        self.ma_type = ma_type.lower()
        
        if self.ma_type not in ['sma', 'ema', 'wma']:
            raise ValueError("ma_type must be 'sma', 'ema', or 'wma'")
    
    @property
    def required_periods(self) -> int:
        return self.period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """이동평균 계산"""
        close_prices = data['close']
        
        if self.ma_type == 'sma':
            return close_prices.rolling(window=self.period).mean()
        
        elif self.ma_type == 'ema':
            return close_prices.ewm(span=self.period).mean()
        
        elif self.ma_type == 'wma':
            # 가중 이동평균
            weights = np.arange(1, self.period + 1)
            return close_prices.rolling(window=self.period).apply(
                lambda x: np.dot(x, weights) / weights.sum(),
                raw=True
            )


class RSI(IIndicator):
    """상대강도지수 (Relative Strength Index)"""
    
    def __init__(self, period: int = 14):
        """
        RSI 초기화
        
        Args:
            period: RSI 계산 기간
        """
        self.period = period
    
    @property
    def required_periods(self) -> int:
        return self.period + 1  # 변화량 계산 위해 +1
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """RSI 계산"""
        close_prices = data['close']
        
        # 가격 변화량 계산
        delta = close_prices.diff()
        
        # 상승분과 하락분 분리
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 평균 상승분과 하락분 계산 (Wilder's smoothing)
        avg_gain = gain.ewm(alpha=1/self.period).mean()
        avg_loss = loss.ewm(alpha=1/self.period).mean()
        
        # RS와 RSI 계산
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class BollingerBands(IIndicator):
    """볼린저 밴드"""
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        """
        볼린저 밴드 초기화
        
        Args:
            period: 이동평균 기간
            num_std: 표준편차 배수
        """
        self.period = period
        self.num_std = num_std
    
    @property
    def required_periods(self) -> int:
        return self.period
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """볼린저 밴드 계산"""
        close_prices = data['close']
        
        # 중심선 (SMA)
        middle = close_prices.rolling(window=self.period).mean()
        
        # 표준편차
        std = close_prices.rolling(window=self.period).std()
        
        # 상단/하단 밴드
        upper = middle + (std * self.num_std)
        lower = middle - (std * self.num_std)
        
        # %B 계산
        percent_b = (close_prices - lower) / (upper - lower)
        
        # 밴드 폭
        bandwidth = (upper - lower) / middle
        
        return pd.DataFrame({
            'bb_middle': middle,
            'bb_upper': upper,
            'bb_lower': lower,
            'bb_percent': percent_b,
            'bb_width': bandwidth
        })


class MACD(IIndicator):
    """MACD (Moving Average Convergence Divergence)"""
    
    def __init__(
        self, 
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        """
        MACD 초기화
        
        Args:
            fast_period: 빠른 EMA 기간
            slow_period: 느린 EMA 기간
            signal_period: 시그널 라인 기간
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    @property
    def required_periods(self) -> int:
        return self.slow_period + self.signal_period
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        close_prices = data['close']
        
        # EMA 계산
        ema_fast = close_prices.ewm(span=self.fast_period).mean()
        ema_slow = close_prices.ewm(span=self.slow_period).mean()
        
        # MACD 라인
        macd_line = ema_fast - ema_slow
        
        # 시그널 라인
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        
        # 히스토그램
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': histogram
        })


class Stochastic(IIndicator):
    """스토캐스틱 오실레이터"""
    
    def __init__(self, k_period: int = 14, d_period: int = 3):
        """
        스토캐스틱 초기화
        
        Args:
            k_period: %K 계산 기간
            d_period: %D 계산 기간
        """
        self.k_period = k_period
        self.d_period = d_period
    
    @property
    def required_periods(self) -> int:
        return self.k_period + self.d_period - 1
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """스토캐스틱 계산"""
        high_prices = data['high']
        low_prices = data['low']
        close_prices = data['close']
        
        # 최고가와 최저가 계산
        highest_high = high_prices.rolling(window=self.k_period).max()
        lowest_low = low_prices.rolling(window=self.k_period).min()
        
        # %K 계산
        k_percent = 100 * (close_prices - lowest_low) / (highest_high - lowest_low)
        
        # %D 계산 (Slow Stochastic)
        d_percent = k_percent.rolling(window=self.d_period).mean()
        
        return pd.DataFrame({
            'stoch_k': k_percent,
            'stoch_d': d_percent
        })


class ATR(IIndicator):
    """평균 진폭 (Average True Range)"""
    
    def __init__(self, period: int = 14):
        """
        ATR 초기화
        
        Args:
            period: ATR 계산 기간
        """
        self.period = period
    
    @property
    def required_periods(self) -> int:
        return self.period + 1  # True Range 계산 위해 +1
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """ATR 계산"""
        high_prices = data['high']
        low_prices = data['low']
        close_prices = data['close']
        
        # True Range 계산
        tr1 = high_prices - low_prices
        tr2 = abs(high_prices - close_prices.shift(1))
        tr3 = abs(low_prices - close_prices.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR 계산 (Wilder's smoothing)
        atr = true_range.ewm(alpha=1/self.period).mean()
        
        return atr


class Williams_R(IIndicator):
    """윌리엄스 %R"""
    
    def __init__(self, period: int = 14):
        """
        윌리엄스 %R 초기화
        
        Args:
            period: 계산 기간
        """
        self.period = period
    
    @property
    def required_periods(self) -> int:
        return self.period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """윌리엄스 %R 계산"""
        high_prices = data['high']
        low_prices = data['low']
        close_prices = data['close']
        
        # 최고가와 최저가 계산
        highest_high = high_prices.rolling(window=self.period).max()
        lowest_low = low_prices.rolling(window=self.period).min()
        
        # %R 계산
        williams_r = -100 * (highest_high - close_prices) / (highest_high - lowest_low)
        
        return williams_r


class CCI(IIndicator):
    """상품 채널 지수 (Commodity Channel Index)"""
    
    def __init__(self, period: int = 20, factor: float = 0.015):
        """
        CCI 초기화
        
        Args:
            period: 계산 기간
            factor: CCI 팩터 (일반적으로 0.015)
        """
        self.period = period
        self.factor = factor
    
    @property
    def required_periods(self) -> int:
        return self.period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """CCI 계산"""
        high_prices = data['high']
        low_prices = data['low']
        close_prices = data['close']
        
        # 전형 가격 (Typical Price)
        typical_price = (high_prices + low_prices + close_prices) / 3
        
        # 이동평균
        sma_tp = typical_price.rolling(window=self.period).mean()
        
        # 평균 편차
        mean_deviation = typical_price.rolling(window=self.period).apply(
            lambda x: np.mean(np.abs(x - x.mean())),
            raw=True
        )
        
        # CCI 계산
        cci = (typical_price - sma_tp) / (self.factor * mean_deviation)
        
        return cci


class IndicatorFactory:
    """지표 팩토리"""
    
    _indicators = {
        'sma': lambda period: MovingAverage(period, 'sma'),
        'ema': lambda period: MovingAverage(period, 'ema'),
        'wma': lambda period: MovingAverage(period, 'wma'),
        'rsi': RSI,
        'bb': BollingerBands,
        'macd': MACD,
        'stoch': Stochastic,
        'atr': ATR,
        'williams_r': Williams_R,
        'cci': CCI
    }
    
    @classmethod
    def create(cls, name: str, **kwargs) -> IIndicator:
        """지표 생성"""
        if name not in cls._indicators:
            raise ValueError(f"Unknown indicator: {name}")
        
        indicator_class = cls._indicators[name]
        
        # 람다 함수인 경우 (이동평균)
        if callable(indicator_class) and not hasattr(indicator_class, '__init__'):
            if 'period' not in kwargs:
                raise ValueError(f"Period required for {name}")
            return indicator_class(kwargs['period'])
        
        return indicator_class(**kwargs)
    
    @classmethod
    def list_indicators(cls) -> list:
        """사용 가능한 지표 목록"""
        return list(cls._indicators.keys())


def calculate_multiple_indicators(
    data: pd.DataFrame, 
    indicators_config: Dict[str, Dict[str, Any]]
) -> pd.DataFrame:
    """
    여러 지표를 한번에 계산
    
    Args:
        data: OHLCV 데이터
        indicators_config: 지표 설정 딕셔너리
            예: {
                'sma_20': {'name': 'sma', 'period': 20},
                'rsi_14': {'name': 'rsi', 'period': 14}
            }
    
    Returns:
        지표가 추가된 데이터프레임
    """
    result = data.copy()
    
    for indicator_name, config in indicators_config.items():
        try:
            # 지표 생성
            name = config.pop('name')
            indicator = IndicatorFactory.create(name, **config)
            
            # 지표 계산
            if indicator.is_ready(data):
                indicator_data = indicator.calculate(data)
                
                if isinstance(indicator_data, pd.Series):
                    result[indicator_name] = indicator_data
                elif isinstance(indicator_data, pd.DataFrame):
                    # 여러 컬럼이 있는 경우 접두사 추가
                    for col in indicator_data.columns:
                        result[f"{indicator_name}_{col}"] = indicator_data[col]
            
        except Exception as e:
            print(f"Error calculating {indicator_name}: {e}")
            continue
    
    return result