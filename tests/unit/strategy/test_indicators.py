# -*- coding: utf-8 -*-
"""
지표 라이브러리 테스트
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from src.strategy.indicators import (
    MovingAverage, RSI, BollingerBands, MACD, Stochastic,
    ATR, Williams_R, CCI, IndicatorFactory, calculate_multiple_indicators
)


class TestMovingAverage:
    """이동평균 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 데이터"""
        return pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })
    
    def test_sma_calculation(self, sample_data):
        """단순이동평균 계산 테스트"""
        ma = MovingAverage(period=5, ma_type="sma")
        result = ma.calculate(sample_data)
        
        # 5일 SMA 계산: (100+102+101+103+105)/5 = 102.2
        expected_first_sma = 102.2
        assert abs(result.iloc[4] - expected_first_sma) < 0.01
        
        # 마지막 5일 SMA: (104+106+108+107+109)/5 = 106.8
        expected_last_sma = 106.8
        assert abs(result.iloc[-1] - expected_last_sma) < 0.01
    
    def test_ema_calculation(self, sample_data):
        """지수이동평균 계산 테스트"""
        ma = MovingAverage(period=5, ma_type="ema")
        result = ma.calculate(sample_data)
        
        # EMA는 pandas EMA와 동일해야 함
        expected = sample_data['close'].ewm(span=5).mean()
        pd.testing.assert_series_equal(result, expected)
    
    def test_wma_calculation(self):
        """가중이동평균 계산 테스트"""
        data = pd.DataFrame({'close': [10, 20, 30, 40, 50]})
        ma = MovingAverage(period=3, ma_type="wma")
        result = ma.calculate(data)
        
        # 3일 WMA: (1*30 + 2*40 + 3*50) / (1+2+3) = 260/6 = 43.33
        expected_wma = 43.33333333
        assert abs(result.iloc[-1] - expected_wma) < 0.01
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        ma = MovingAverage(period=20)
        assert ma.required_periods == 20
    
    def test_invalid_ma_type(self):
        """잘못된 이동평균 타입 테스트"""
        with pytest.raises(ValueError):
            MovingAverage(period=10, ma_type="invalid")
    
    def test_insufficient_data(self):
        """데이터 부족 테스트"""
        data = pd.DataFrame({'close': [100, 102, 101]})
        ma = MovingAverage(period=5)
        
        assert not ma.is_ready(data)
        result = ma.calculate(data)
        assert result.iloc[:4].isna().all()


class TestRSI:
    """RSI 테스트"""
    
    @pytest.fixture
    def trending_data(self):
        """상승 추세 데이터"""
        # 상승 추세 생성
        prices = [100]
        for i in range(20):
            change = np.random.uniform(0.5, 2.0)  # 항상 상승
            prices.append(prices[-1] + change)
        
        return pd.DataFrame({'close': prices})
    
    @pytest.fixture
    def volatile_data(self):
        """변동성 데이터"""
        return pd.DataFrame({
            'close': [100, 105, 98, 102, 99, 104, 96, 108, 103, 101,
                     106, 99, 103, 97, 105, 102, 98, 104, 100, 107]
        })
    
    def test_rsi_calculation(self, volatile_data):
        """RSI 계산 테스트"""
        rsi = RSI(period=14)
        result = rsi.calculate(volatile_data)
        
        # RSI는 0-100 범위여야 함
        valid_rsi = result.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_rsi_extreme_values(self, trending_data):
        """RSI 극값 테스트"""
        rsi = RSI(period=14)
        result = rsi.calculate(trending_data)
        
        # 지속적인 상승 추세에서 RSI는 높은 값을 가져야 함
        last_rsi = result.iloc[-1]
        assert last_rsi > 50  # 상승 추세이므로 50 이상
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        rsi = RSI(period=14)
        assert rsi.required_periods == 15  # period + 1
    
    def test_rsi_with_no_change(self):
        """가격 변화 없는 경우 테스트"""
        data = pd.DataFrame({'close': [100] * 20})
        rsi = RSI(period=14)
        result = rsi.calculate(data)
        
        # 가격 변화가 없으면 RSI는 NaN이거나 50이어야 함
        last_rsi = result.iloc[-1]
        assert np.isnan(last_rsi) or abs(last_rsi - 50) < 0.01


class TestBollingerBands:
    """볼린저 밴드 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 데이터"""
        return pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                     110, 108, 111, 109, 112, 114, 113, 115, 117, 116]
        })
    
    def test_bollinger_bands_calculation(self, sample_data):
        """볼린저 밴드 계산 테스트"""
        bb = BollingerBands(period=10, num_std=2.0)
        result = bb.calculate(sample_data)
        
        # 결과에 필요한 컬럼들이 있는지 확인
        expected_columns = ['bb_middle', 'bb_upper', 'bb_lower', 'bb_percent', 'bb_width']
        for col in expected_columns:
            assert col in result.columns
        
        # 상단 밴드 > 중간선 > 하단 밴드
        valid_data = result.dropna()
        assert (valid_data['bb_upper'] > valid_data['bb_middle']).all()
        assert (valid_data['bb_middle'] > valid_data['bb_lower']).all()
    
    def test_bb_percent_range(self, sample_data):
        """%B 범위 테스트"""
        bb = BollingerBands(period=10, num_std=2.0)
        result = bb.calculate(sample_data)
        
        # %B는 일반적으로 0-1 범위이지만 밴드를 벗어날 수 있음
        percent_b = result['bb_percent'].dropna()
        
        # 대부분의 값이 합리적 범위에 있어야 함
        reasonable_range = (percent_b >= -0.5) & (percent_b <= 1.5)
        assert reasonable_range.mean() > 0.8  # 80% 이상이 합리적 범위
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        bb = BollingerBands(period=20)
        assert bb.required_periods == 20
    
    def test_different_std_multipliers(self, sample_data):
        """다른 표준편차 배수 테스트"""
        bb1 = BollingerBands(period=10, num_std=1.0)
        bb2 = BollingerBands(period=10, num_std=2.0)
        
        result1 = bb1.calculate(sample_data)
        result2 = bb2.calculate(sample_data)
        
        # 표준편차 배수가 클수록 밴드가 더 넓어야 함
        width1 = result1['bb_width'].iloc[-1]
        width2 = result2['bb_width'].iloc[-1]
        assert width2 > width1


class TestMACD:
    """MACD 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 데이터"""
        return pd.DataFrame({
            'close': [100 + i + np.sin(i/3) * 5 for i in range(50)]
        })
    
    def test_macd_calculation(self, sample_data):
        """MACD 계산 테스트"""
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        result = macd.calculate(sample_data)
        
        # 결과에 필요한 컬럼들이 있는지 확인
        expected_columns = ['macd', 'macd_signal', 'macd_histogram']
        for col in expected_columns:
            assert col in result.columns
        
        # 히스토그램 = MACD - Signal
        valid_data = result.dropna()
        histogram_check = valid_data['macd'] - valid_data['macd_signal']
        pd.testing.assert_series_equal(
            valid_data['macd_histogram'], 
            histogram_check, 
            check_names=False
        )
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        assert macd.required_periods == 35  # slow + signal


class TestStochastic:
    """스토캐스틱 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 OHLC 데이터"""
        return pd.DataFrame({
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })
    
    def test_stochastic_calculation(self, sample_data):
        """스토캐스틱 계산 테스트"""
        stoch = Stochastic(k_period=5, d_period=3)
        result = stoch.calculate(sample_data)
        
        # 결과에 필요한 컬럼들이 있는지 확인
        assert 'stoch_k' in result.columns
        assert 'stoch_d' in result.columns
        
        # %K와 %D는 0-100 범위여야 함
        valid_data = result.dropna()
        assert (valid_data['stoch_k'] >= 0).all()
        assert (valid_data['stoch_k'] <= 100).all()
        assert (valid_data['stoch_d'] >= 0).all()
        assert (valid_data['stoch_d'] <= 100).all()
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        stoch = Stochastic(k_period=14, d_period=3)
        assert stoch.required_periods == 16  # k_period + d_period - 1


class TestATR:
    """ATR 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 OHLC 데이터"""
        return pd.DataFrame({
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })
    
    def test_atr_calculation(self, sample_data):
        """ATR 계산 테스트"""
        atr = ATR(period=14)
        result = atr.calculate(sample_data)
        
        # ATR은 항상 양수여야 함
        valid_atr = result.dropna()
        assert (valid_atr >= 0).all()
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        atr = ATR(period=14)
        assert atr.required_periods == 15  # period + 1


class TestWilliamsR:
    """윌리엄스 %R 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 OHLC 데이터"""
        return pd.DataFrame({
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })
    
    def test_williams_r_calculation(self, sample_data):
        """윌리엄스 %R 계산 테스트"""
        wr = Williams_R(period=14)
        result = wr.calculate(sample_data)
        
        # %R은 -100 ~ 0 범위여야 함
        valid_wr = result.dropna()
        assert (valid_wr >= -100).all()
        assert (valid_wr <= 0).all()
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        wr = Williams_R(period=14)
        assert wr.required_periods == 14


class TestCCI:
    """CCI 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 OHLC 데이터"""
        return pd.DataFrame({
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })
    
    def test_cci_calculation(self, sample_data):
        """CCI 계산 테스트"""
        cci = CCI(period=5)  # 데이터 길이에 맞게 조정
        result = cci.calculate(sample_data)
        
        # CCI는 임의의 범위를 가질 수 있지만 일반적으로 -200 ~ +200
        valid_cci = result.dropna()
        assert len(valid_cci) > 0
        
        # 극값이 너무 크지 않은지 확인
        assert abs(valid_cci.max()) < 1000
        assert abs(valid_cci.min()) < 1000
    
    def test_required_periods(self):
        """필요 기간 테스트"""
        cci = CCI(period=20)
        assert cci.required_periods == 20


class TestIndicatorFactory:
    """지표 팩토리 테스트"""
    
    def test_create_sma(self):
        """SMA 생성 테스트"""
        indicator = IndicatorFactory.create('sma', period=20)
        assert isinstance(indicator, MovingAverage)
        assert indicator.period == 20
        assert indicator.ma_type == 'sma'
    
    def test_create_ema(self):
        """EMA 생성 테스트"""
        indicator = IndicatorFactory.create('ema', period=12)
        assert isinstance(indicator, MovingAverage)
        assert indicator.period == 12
        assert indicator.ma_type == 'ema'
    
    def test_create_rsi(self):
        """RSI 생성 테스트"""
        indicator = IndicatorFactory.create('rsi', period=14)
        assert isinstance(indicator, RSI)
        assert indicator.period == 14
    
    def test_create_bollinger_bands(self):
        """볼린저 밴드 생성 테스트"""
        indicator = IndicatorFactory.create('bb', period=20, num_std=2.5)
        assert isinstance(indicator, BollingerBands)
        assert indicator.period == 20
        assert indicator.num_std == 2.5
    
    def test_create_macd(self):
        """MACD 생성 테스트"""
        indicator = IndicatorFactory.create('macd', fast_period=10, slow_period=20, signal_period=5)
        assert isinstance(indicator, MACD)
        assert indicator.fast_period == 10
        assert indicator.slow_period == 20
        assert indicator.signal_period == 5
    
    def test_unknown_indicator(self):
        """알 수 없는 지표 테스트"""
        with pytest.raises(ValueError):
            IndicatorFactory.create('unknown_indicator')
    
    def test_missing_parameters(self):
        """필수 파라미터 누락 테스트"""
        with pytest.raises((ValueError, TypeError)):
            IndicatorFactory.create('sma')  # period 누락
    
    def test_list_indicators(self):
        """지표 목록 테스트"""
        indicators = IndicatorFactory.list_indicators()
        assert 'sma' in indicators
        assert 'ema' in indicators
        assert 'rsi' in indicators
        assert 'bb' in indicators
        assert 'macd' in indicators


class TestMultipleIndicators:
    """다중 지표 계산 테스트"""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 OHLCV 데이터"""
        return pd.DataFrame({
            'open': [99, 101, 100, 102, 104, 103, 105, 107, 106, 108],
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
            'volume': [1000, 1100, 950, 1200, 1300, 1150, 1250, 1400, 1350, 1450]
        })
    
    def test_calculate_multiple_indicators(self, sample_data):
        """다중 지표 계산 테스트"""
        indicators_config = {
            'sma_20': {'name': 'sma', 'period': 5},
            'rsi_14': {'name': 'rsi', 'period': 5},
            'bb_20': {'name': 'bb', 'period': 5, 'num_std': 2.0}
        }
        
        result = calculate_multiple_indicators(sample_data, indicators_config)
        
        # 원본 컬럼들이 유지되는지 확인
        for col in sample_data.columns:
            assert col in result.columns
        
        # 새로운 지표 컬럼들이 추가되었는지 확인
        assert 'sma_20' in result.columns
        assert 'rsi_14' in result.columns
        assert 'bb_20_bb_middle' in result.columns  # BB는 여러 컬럼 생성
        assert 'bb_20_bb_upper' in result.columns
        assert 'bb_20_bb_lower' in result.columns
    
    def test_error_handling_in_multiple_indicators(self, sample_data):
        """다중 지표 계산 오류 처리 테스트"""
        indicators_config = {
            'invalid_indicator': {'name': 'invalid', 'period': 10},
            'valid_sma': {'name': 'sma', 'period': 5}
        }
        
        # 오류가 발생해도 유효한 지표는 계산되어야 함
        result = calculate_multiple_indicators(sample_data, indicators_config)
        
        # 유효한 지표는 추가되어야 함
        assert 'valid_sma' in result.columns
        
        # 무효한 지표는 추가되지 않아야 함
        assert 'invalid_indicator' not in result.columns


# 통합 테스트
class TestIndicatorsIntegration:
    """지표 통합 테스트"""
    
    @pytest.fixture
    def market_data(self):
        """실제와 유사한 시장 데이터"""
        np.random.seed(42)  # 재현 가능한 결과
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.02)  # 랜덤 워크
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.randn() * 0.01))
            low = price * (1 - abs(np.random.randn() * 0.01))
            volume = int(1000000 + np.random.randn() * 100000)
            
            data.append({
                'date': dates[i],
                'open': prices[i-1] if i > 0 else price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_all_indicators_with_real_data(self, market_data):
        """실제 데이터로 모든 지표 테스트"""
        # 모든 지표 계산
        indicators_config = {
            'sma_20': {'name': 'sma', 'period': 20},
            'ema_12': {'name': 'ema', 'period': 12},
            'rsi_14': {'name': 'rsi', 'period': 14},
            'bb_20': {'name': 'bb', 'period': 20},
            'macd': {'name': 'macd'},
            'stoch': {'name': 'stoch'},
            'atr': {'name': 'atr'},
            'williams_r': {'name': 'williams_r'},
            'cci': {'name': 'cci'}
        }
        
        result = calculate_multiple_indicators(market_data, indicators_config)
        
        # 모든 지표가 계산되었는지 확인
        assert 'sma_20' in result.columns
        assert 'ema_12' in result.columns
        assert 'rsi_14' in result.columns
        assert 'atr' in result.columns
        
        # 데이터 품질 확인
        assert len(result) == len(market_data)
        assert not result['close'].isna().any()
        
        # 지표 값들이 합리적 범위에 있는지 확인
        rsi_values = result['rsi_14'].dropna()
        assert (rsi_values >= 0).all() and (rsi_values <= 100).all()
        
        atr_values = result['atr'].dropna()
        assert (atr_values >= 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])