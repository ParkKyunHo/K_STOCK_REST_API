# -*- coding: utf-8 -*-
"""
데이터 정규화기 테스트
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

import pytest

from src.application.data.data_normalizer import (
    DataNormalizer,
    DataNormalizationError
)
from src.core.models.market_data import Quote, OHLCV


class TestDataNormalizer:
    """DataNormalizer 테스트"""
    
    @pytest.fixture
    def normalizer(self):
        """데이터 정규화기"""
        return DataNormalizer()
    
    @pytest.fixture
    def raw_quote_data(self):
        """키움 API 원시 현재가 데이터"""
        return {
            "hts_kor_isnm": "삼성전자",
            "stck_prpr": "70,000",           # 현재가 (쉼표 포함)
            "prdy_vrss": "1,000",            # 전일대비
            "prdy_vrss_sign": "2",           # 부호 (상승)
            "prdy_ctrt": "1.45",             # 전일대비율
            "stck_oprc": "69,500",           # 시가
            "stck_hgpr": "70,500",           # 고가
            "stck_lwpr": "69,000",           # 저가
            "acml_vol": "1,000,000",         # 누적거래량
            "acml_tr_pbmn": "70,000,000,000", # 누적거래대금
            "hts_avls": "4,200,000,000,000", # 시가총액 (선택)
            "lstn_stcn": "5,969,782,550"     # 상장주식수 (선택)
        }
    
    @pytest.fixture
    def raw_ohlcv_data(self):
        """키움 API 원시 OHLCV 데이터"""
        return {
            "stck_bsop_date": "20231201",    # 영업일자
            "stck_clpr": "70,000",           # 종가
            "stck_oprc": "69,500",           # 시가
            "stck_hgpr": "70,500",           # 고가
            "stck_lwpr": "69,000",           # 저가
            "acml_vol": "1,000,000",         # 거래량
            "acml_tr_pbmn": "70,000,000,000" # 거래대금
        }
    
    def test_normalize_quote_data(self, normalizer, raw_quote_data):
        """현재가 데이터 정규화 테스트"""
        symbol = "005930"
        
        quote = normalizer.normalize_quote_data(symbol, raw_quote_data)
        
        assert isinstance(quote, Quote)
        assert quote.symbol == symbol
        assert quote.price == Decimal("70000")
        assert quote.prev_close == Decimal("69000")  # 70000 - 1000
        assert quote.change == Decimal("1000")
        assert quote.change_rate == Decimal("1.45")
        assert quote.volume == 1000000
        assert quote.trade_value == Decimal("70000000000")
        assert quote.open_price == Decimal("69500")
        assert quote.high_price == Decimal("70500")
        assert quote.low_price == Decimal("69000")
        assert quote.market_cap == Decimal("4200000000000")
        assert quote.shares_outstanding == 5969782550
        assert quote.data_type == "quote"
        assert quote.source == "kiwoom"
    
    def test_normalize_ohlcv_data(self, normalizer, raw_ohlcv_data):
        """OHLCV 데이터 정규화 테스트"""
        symbol = "005930"
        
        ohlcv = normalizer.normalize_ohlcv_data(symbol, raw_ohlcv_data)
        
        assert isinstance(ohlcv, OHLCV)
        assert ohlcv.symbol == symbol
        assert ohlcv.timestamp.date() == datetime(2023, 12, 1).date()
        assert ohlcv.open_price == Decimal("69500")
        assert ohlcv.high_price == Decimal("70500")
        assert ohlcv.low_price == Decimal("69000")
        assert ohlcv.close_price == Decimal("70000")
        assert ohlcv.volume == 1000000
        assert ohlcv.trade_value == Decimal("70000000000")
        assert ohlcv.period == "1D"
        assert ohlcv.data_type == "ohlcv"
        assert ohlcv.source == "kiwoom"
    
    def test_parse_decimal_with_commas(self, normalizer):
        """쉼표 포함 숫자 파싱 테스트"""
        # 정상 케이스
        assert normalizer._parse_decimal("70,000") == Decimal("70000")
        assert normalizer._parse_decimal("1,234,567.89") == Decimal("1234567.89")
        assert normalizer._parse_decimal("0") == Decimal("0")
        assert normalizer._parse_decimal("100") == Decimal("100")
        
        # 빈 문자열
        assert normalizer._parse_decimal("") == Decimal("0")
        assert normalizer._parse_decimal("   ") == Decimal("0")
    
    def test_parse_decimal_invalid(self, normalizer):
        """잘못된 숫자 파싱 에러 테스트"""
        with pytest.raises(DataNormalizationError):
            normalizer._parse_decimal("INVALID")
        
        with pytest.raises(DataNormalizationError):
            normalizer._parse_decimal("12.34.56")
    
    def test_parse_int_with_commas(self, normalizer):
        """쉼표 포함 정수 파싱 테스트"""
        # 정상 케이스
        assert normalizer._parse_int("1,000,000") == 1000000
        assert normalizer._parse_int("0") == 0
        assert normalizer._parse_int("123") == 123
        
        # 빈 문자열
        assert normalizer._parse_int("") == 0
        assert normalizer._parse_int("   ") == 0
    
    def test_parse_int_invalid(self, normalizer):
        """잘못된 정수 파싱 에러 테스트"""
        with pytest.raises(DataNormalizationError):
            normalizer._parse_int("INVALID")
        
        with pytest.raises(DataNormalizationError):
            normalizer._parse_int("12.34")
    
    def test_calculate_prev_close_rising(self, normalizer):
        """전일종가 계산 - 상승장 테스트"""
        current = Decimal("70000")
        change = Decimal("1000")
        
        # 상승 (부호 2)
        prev_close = normalizer._calculate_prev_close(current, change, "2")
        assert prev_close == Decimal("69000")  # 70000 - 1000
        
        # 상한가 (부호 1)
        prev_close = normalizer._calculate_prev_close(current, change, "1")
        assert prev_close == Decimal("69000")
    
    def test_calculate_prev_close_falling(self, normalizer):
        """전일종가 계산 - 하락장 테스트"""
        current = Decimal("69000")
        change = Decimal("1000")
        
        # 하락 (부호 5)
        prev_close = normalizer._calculate_prev_close(current, change, "5")
        assert prev_close == Decimal("70000")  # 69000 + 1000
        
        # 하한가 (부호 4)
        prev_close = normalizer._calculate_prev_close(current, change, "4")
        assert prev_close == Decimal("70000")
    
    def test_calculate_prev_close_unchanged(self, normalizer):
        """전일종가 계산 - 보합 테스트"""
        current = Decimal("70000")
        change = Decimal("0")
        
        # 보합 (부호 3)
        prev_close = normalizer._calculate_prev_close(current, change, "3")
        assert prev_close == Decimal("70000")
        
        # 알 수 없는 부호
        prev_close = normalizer._calculate_prev_close(current, change, "9")
        assert prev_close == Decimal("70000")
    
    def test_parse_date_yyyymmdd(self, normalizer):
        """YYYYMMDD 날짜 파싱 테스트"""
        # 정상 케이스
        date = normalizer._parse_date_yyyymmdd("20231201")
        assert date == datetime(2023, 12, 1)
        
        date = normalizer._parse_date_yyyymmdd("20240229")  # 윤년
        assert date == datetime(2024, 2, 29)
    
    def test_parse_date_yyyymmdd_invalid(self, normalizer):
        """잘못된 날짜 파싱 에러 테스트"""
        with pytest.raises(DataNormalizationError):
            normalizer._parse_date_yyyymmdd("INVALID")
        
        with pytest.raises(DataNormalizationError):
            normalizer._parse_date_yyyymmdd("20231301")  # 13월
        
        with pytest.raises(DataNormalizationError):
            normalizer._parse_date_yyyymmdd("20230229")  # 평년 2월 29일
    
    def test_normalize_quote_missing_fields(self, normalizer):
        """필수 필드 누락 시 에러 테스트"""
        incomplete_data = {
            "stck_prpr": "70000",
            # prdy_vrss 누락
        }
        
        with pytest.raises(DataNormalizationError) as exc_info:
            normalizer.normalize_quote_data("005930", incomplete_data)
        
        assert "missing required field" in str(exc_info.value).lower()
    
    def test_normalize_ohlcv_missing_fields(self, normalizer):
        """필수 필드 누락 시 에러 테스트"""
        incomplete_data = {
            "stck_bsop_date": "20231201",
            # stck_clpr 누락
        }
        
        with pytest.raises(DataNormalizationError) as exc_info:
            normalizer.normalize_ohlcv_data("005930", incomplete_data)
        
        assert "missing required field" in str(exc_info.value).lower()
    
    def test_optional_fields_handling(self, normalizer):
        """선택적 필드 처리 테스트"""
        minimal_quote_data = {
            "stck_prpr": "70000",
            "prdy_vrss": "1000", 
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "1.45",
            "stck_oprc": "69500",
            "stck_hgpr": "70500",
            "stck_lwpr": "69000",
            "acml_vol": "1000000",
            "acml_tr_pbmn": "70000000000"
            # 선택적 필드들 (hts_avls, lstn_stcn) 누락
        }
        
        quote = normalizer.normalize_quote_data("005930", minimal_quote_data)
        
        assert quote.market_cap is None
        assert quote.shares_outstanding is None
        assert quote.price == Decimal("70000")  # 필수 필드는 정상 처리
    
    def test_data_normalization_error(self):
        """DataNormalizationError 테스트"""
        error = DataNormalizationError("Test error", "TEST_FIELD")
        assert str(error) == "Test error"
        assert error.field_name == "TEST_FIELD"