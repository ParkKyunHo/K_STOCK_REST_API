# -*- coding: utf-8 -*-
"""
데이터 정규화기 - API 응답을 표준 모델로 변환
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from src.core.models.market_data import Quote, OHLCV

logger = logging.getLogger(__name__)


class DataNormalizationError(Exception):
    """데이터 정규화 에러"""
    
    def __init__(self, message: str, field_name: Optional[str] = None):
        super().__init__(message)
        self.field_name = field_name


class DataNormalizer:
    """API 응답 데이터를 표준 모델로 정규화"""
    
    def normalize_quote_data(self, symbol: str, raw_data: Dict[str, Any]) -> Quote:
        """
        키움 API 현재가 응답을 Quote 모델로 변환
        
        Args:
            symbol: 종목 코드
            raw_data: 키움 API 원시 응답 데이터
            
        Returns:
            정규화된 Quote 객체
            
        Raises:
            DataNormalizationError: 데이터 변환 실패 시
        """
        try:
            # 필수 필드 검증
            required_fields = [
                "stck_prpr", "prdy_vrss", "prdy_vrss_sign", "prdy_ctrt",
                "stck_oprc", "stck_hgpr", "stck_lwpr", "acml_vol", "acml_tr_pbmn"
            ]
            
            for field in required_fields:
                if field not in raw_data:
                    raise DataNormalizationError(f"Missing required field: {field}", field)
            
            # 기본 정보 파싱
            current_price = self._parse_decimal(raw_data["stck_prpr"])
            change = self._parse_decimal(raw_data["prdy_vrss"])
            sign = raw_data["prdy_vrss_sign"]
            
            # 전일종가 계산
            prev_close = self._calculate_prev_close(current_price, change, sign)
            
            # Quote 객체 생성
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                data_type="quote",
                source="kiwoom",
                price=current_price,
                prev_close=prev_close,
                change=change,
                change_rate=self._parse_decimal(raw_data["prdy_ctrt"]),
                volume=self._parse_int(raw_data["acml_vol"]),
                trade_value=self._parse_decimal(raw_data["acml_tr_pbmn"]),
                open_price=self._parse_decimal(raw_data["stck_oprc"]),
                high_price=self._parse_decimal(raw_data["stck_hgpr"]),
                low_price=self._parse_decimal(raw_data["stck_lwpr"]),
                market_cap=self._parse_decimal_optional(raw_data.get("hts_avls")),
                shares_outstanding=self._parse_int_optional(raw_data.get("lstn_stcn"))
            )
            
            logger.debug(f"Normalized quote data for {symbol}: {quote.price}")
            return quote
            
        except DataNormalizationError:
            raise
        except Exception as e:
            logger.error(f"Failed to normalize quote data for {symbol}: {e}")
            raise DataNormalizationError(f"Quote normalization failed: {e}")
    
    def normalize_ohlcv_data(
        self, 
        symbol: str, 
        raw_data: Dict[str, Any],
        period: str = "1D"
    ) -> OHLCV:
        """
        키움 API OHLCV 응답을 OHLCV 모델로 변환
        
        Args:
            symbol: 종목 코드
            raw_data: 키움 API 원시 응답 데이터
            period: 데이터 주기
            
        Returns:
            정규화된 OHLCV 객체
            
        Raises:
            DataNormalizationError: 데이터 변환 실패 시
        """
        try:
            # 필수 필드 검증
            required_fields = [
                "stck_bsop_date", "stck_oprc", "stck_hgpr", 
                "stck_lwpr", "stck_clpr", "acml_vol", "acml_tr_pbmn"
            ]
            
            for field in required_fields:
                if field not in raw_data:
                    raise DataNormalizationError(f"Missing required field: {field}", field)
            
            # 날짜 파싱
            date = self._parse_date_yyyymmdd(raw_data["stck_bsop_date"])
            
            # OHLCV 객체 생성
            ohlcv = OHLCV(
                symbol=symbol,
                timestamp=date,
                data_type="ohlcv",
                source="kiwoom",
                open_price=self._parse_decimal(raw_data["stck_oprc"]),
                high_price=self._parse_decimal(raw_data["stck_hgpr"]),
                low_price=self._parse_decimal(raw_data["stck_lwpr"]),
                close_price=self._parse_decimal(raw_data["stck_clpr"]),
                volume=self._parse_int(raw_data["acml_vol"]),
                trade_value=self._parse_decimal(raw_data["acml_tr_pbmn"]),
                period=period
            )
            
            logger.debug(f"Normalized OHLCV data for {symbol} on {date.date()}")
            return ohlcv
            
        except DataNormalizationError:
            raise
        except Exception as e:
            logger.error(f"Failed to normalize OHLCV data for {symbol}: {e}")
            raise DataNormalizationError(f"OHLCV normalization failed: {e}")
    
    def _parse_decimal(self, value: str) -> Decimal:
        """
        문자열을 Decimal로 변환 (쉼표 제거)
        
        Args:
            value: 변환할 문자열
            
        Returns:
            Decimal 값
            
        Raises:
            DataNormalizationError: 변환 실패 시
        """
        try:
            if not value or not value.strip():
                return Decimal("0")
            
            # 쉼표 제거 후 변환
            clean_value = str(value).replace(",", "").strip()
            return Decimal(clean_value)
            
        except (InvalidOperation, ValueError) as e:
            raise DataNormalizationError(f"Invalid decimal value: {value}")
    
    def _parse_decimal_optional(self, value: Optional[str]) -> Optional[Decimal]:
        """
        선택적 Decimal 파싱
        
        Args:
            value: 변환할 문자열 (None 가능)
            
        Returns:
            Decimal 값 또는 None
        """
        if not value:
            return None
        try:
            return self._parse_decimal(value)
        except DataNormalizationError:
            return None
    
    def _parse_int(self, value: str) -> int:
        """
        문자열을 int로 변환 (쉼표 제거)
        
        Args:
            value: 변환할 문자열
            
        Returns:
            정수 값
            
        Raises:
            DataNormalizationError: 변환 실패 시
        """
        try:
            if not value or not value.strip():
                return 0
            
            # 쉼표 제거 후 변환
            clean_value = str(value).replace(",", "").strip()
            return int(float(clean_value))  # float 거쳐서 소수점 처리
            
        except (ValueError, TypeError) as e:
            raise DataNormalizationError(f"Invalid integer value: {value}")
    
    def _parse_int_optional(self, value: Optional[str]) -> Optional[int]:
        """
        선택적 int 파싱
        
        Args:
            value: 변환할 문자열 (None 가능)
            
        Returns:
            정수 값 또는 None
        """
        if not value:
            return None
        try:
            return self._parse_int(value)
        except DataNormalizationError:
            return None
    
    def _calculate_prev_close(self, current_price: Decimal, change: Decimal, sign: str) -> Decimal:
        """
        전일종가 계산
        
        Args:
            current_price: 현재가
            change: 전일대비 변동
            sign: 변동 부호
            
        Returns:
            전일종가
        """
        try:
            # 키움 API 부호 코드
            # 1: 상한가, 2: 상승, 3: 보합, 4: 하한가, 5: 하락
            if sign in ["1", "2"]:  # 상승/상한가
                return current_price - change
            elif sign in ["4", "5"]:  # 하락/하한가
                return current_price + abs(change)
            else:  # 보합 또는 기타
                return current_price
                
        except Exception:
            # 계산 실패 시 현재가 반환
            return current_price
    
    def _parse_date_yyyymmdd(self, date_str: str) -> datetime:
        """
        YYYYMMDD 형식 날짜 문자열을 datetime으로 변환
        
        Args:
            date_str: YYYYMMDD 형식 날짜 문자열
            
        Returns:
            datetime 객체
            
        Raises:
            DataNormalizationError: 날짜 파싱 실패 시
        """
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError as e:
            raise DataNormalizationError(f"Invalid date format: {date_str}")