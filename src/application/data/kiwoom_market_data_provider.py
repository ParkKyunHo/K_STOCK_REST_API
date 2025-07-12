"""
키움증권 마켓 데이터 제공자
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import AsyncGenerator, Dict, List, Optional, Set, Union

from src.core.interfaces.market_data import IMarketDataProvider
from src.core.models.market_data import OHLCV, DataPoint, Quote
from src.infrastructure.api.client.kiwoom_api_client import KiwoomAPIClient

logger = logging.getLogger(__name__)


class DataProviderError(Exception):
    """데이터 제공자 에러"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class KiwoomMarketDataProvider(IMarketDataProvider):
    """키움증권 마켓 데이터 제공자"""
    
    def __init__(
        self,
        api_client: KiwoomAPIClient,
        cache_ttl: float = 5.0  # 5초 캐시
    ):
        """
        초기화
        
        Args:
            api_client: 키움 API 클라이언트
            cache_ttl: 캐시 유효시간 (초)
        """
        self.api_client = api_client
        self.cache_ttl = cache_ttl
        
        # 상태 관리
        self._connected = False
        self.subscribed_symbols: Set[str] = set()
        
        # 캐시
        self._cache: Dict[str, Dict] = {}
        self._cache_lock = asyncio.Lock()
        
        logger.info("KiwoomMarketDataProvider initialized")
    
    async def connect(self) -> bool:
        """
        데이터 소스에 연결
        
        Returns:
            연결 성공 여부
        """
        try:
            await self.api_client.initialize()
            self._connected = True
            logger.info("Connected to Kiwoom API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kiwoom API: {e}")
            return False
    
    async def disconnect(self) -> None:
        """데이터 소스 연결 해제"""
        try:
            if hasattr(self.api_client, 'close'):
                await self.api_client.close()
            
            self._connected = False
            self.subscribed_symbols.clear()
            self._cache.clear()
            
            logger.info("Disconnected from Kiwoom API")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def subscribe(self, symbols: List[str], data_type: str = "quote") -> bool:
        """
        실시간 데이터 구독
        
        Args:
            symbols: 구독할 종목 코드 리스트
            data_type: 데이터 타입 (quote, orderbook, trade 등)
            
        Returns:
            구독 성공 여부
        """
        if not self._connected:
            raise DataProviderError("Provider is not connected")
        
        try:
            # 실시간 구독은 WebSocket 연결이 필요하지만
            # 현재는 간단히 구독 목록에만 추가
            for symbol in symbols:
                self.subscribed_symbols.add(symbol)
            
            logger.info(f"Subscribed to {len(symbols)} symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            return False
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        실시간 데이터 구독 해제
        
        Args:
            symbols: 구독 해제할 종목 코드 리스트
            
        Returns:
            구독 해제 성공 여부
        """
        try:
            for symbol in symbols:
                self.subscribed_symbols.discard(symbol)
            
            logger.info(f"Unsubscribed from {len(symbols)} symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False
    
    async def get_latest_data(self, symbol: str, data_type: str) -> Optional[DataPoint]:
        """
        최신 데이터 조회 (캐시 우선)
        
        Args:
            symbol: 종목 코드
            data_type: 데이터 타입
            
        Returns:
            최신 데이터 포인트
        """
        cache_key = f"{symbol}:{data_type}"
        
        # 캐시 확인
        async with self._cache_lock:
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                age = datetime.now().timestamp() - cache_entry["timestamp"]
                
                if age < self.cache_ttl:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cache_entry["data"]
                else:
                    # 만료된 캐시 삭제
                    del self._cache[cache_key]
        
        # 새 데이터 요청
        if data_type == "quote":
            quote = await self.get_quote(symbol)
            data_point = DataPoint(quote)
        else:
            logger.warning(f"Unsupported data type for latest data: {data_type}")
            return None
        
        # 캐시 저장
        async with self._cache_lock:
            self._cache[cache_key] = {
                "data": data_point,
                "timestamp": datetime.now().timestamp()
            }
        
        return data_point
    
    async def get_historical_data(
        self,
        symbol: str,
        data_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> AsyncGenerator[List[DataPoint], None]:
        """
        과거 데이터 조회 (제너레이터)
        
        Args:
            symbol: 종목 코드
            data_type: 데이터 타입
            start_date: 시작일
            end_date: 종료일
            
        Yields:
            데이터 포인트 리스트 (배치)
        """
        if not self._connected:
            raise DataProviderError("Provider is not connected")
        
        if data_type == "1D":
            # 일봉 데이터 수집
            async for ohlcv_batch in self._get_daily_ohlcv_continuous(symbol, start_date, end_date):
                data_points = [DataPoint(ohlcv) for ohlcv in ohlcv_batch]
                yield data_points
        else:
            logger.warning(f"Unsupported historical data type: {data_type}")
            return
    
    async def get_quote(self, symbol: str) -> Quote:
        """
        현재가 조회
        
        Args:
            symbol: 종목 코드
            
        Returns:
            현재가 데이터
        """
        if not self._connected:
            raise DataProviderError("Provider is not connected")
        
        try:
            # 키움 API 호출 (ka10001: 주식기본정보)
            response = await self.api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": symbol}
            )
            
            # API 에러 확인
            if response.get("rt_cd") != "0":
                error_msg = response.get("msg1", "Unknown error")
                raise DataProviderError(f"API Error: {error_msg}", response.get("msg_cd"))
            
            # 응답 데이터 파싱
            output = response["output"]
            
            # 현재가 데이터 생성
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                data_type="quote",
                source="kiwoom",
                price=self._parse_decimal(output["stck_prpr"]),
                prev_close=self._calculate_prev_close(
                    self._parse_decimal(output["stck_prpr"]),
                    self._parse_decimal(output["prdy_vrss"]),
                    output["prdy_vrss_sign"]
                ),
                change=self._parse_decimal(output["prdy_vrss"]),
                change_rate=self._parse_decimal(output["prdy_ctrt"]),
                volume=self._parse_int(output["acml_vol"]),
                trade_value=self._parse_decimal(output["acml_tr_pbmn"]),
                open_price=self._parse_decimal(output["stck_oprc"]),
                high_price=self._parse_decimal(output["stck_hgpr"]),
                low_price=self._parse_decimal(output["stck_lwpr"]),
                market_cap=self._parse_decimal_optional(output.get("hts_avls")),
                shares_outstanding=self._parse_int_optional(output.get("lstn_stcn"))
            )
            
            logger.debug(f"Retrieved quote for {symbol}: {quote.price}")
            return quote
            
        except DataProviderError:
            raise
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise DataProviderError(f"Failed to get quote: {e}")
    
    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1D",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[OHLCV]:
        """
        OHLCV 데이터 조회
        
        Args:
            symbol: 종목 코드
            period: 기간 ('1D', '1H', '1m' etc.)
            start_date: 시작일
            end_date: 종료일
            limit: 최대 개수
            
        Returns:
            OHLCV 데이터 리스트
        """
        if not self._connected:
            raise DataProviderError("Provider is not connected")
        
        try:
            # API ID 결정
            if period == "1D":
                api_id = "ka10002"  # 일봉차트
            else:
                raise DataProviderError(f"Unsupported period: {period}")
            
            # API 호출
            response = await self.api_client.request(
                api_id=api_id,
                params={
                    "FID_INPUT_ISCD": symbol,
                    "FID_PERIOD_DIV_CODE": "D" if period == "1D" else "m",
                    "FID_ORG_ADJ_PRC": "1"  # 수정주가 반영
                }
            )
            
            # API 에러 확인
            if response.get("rt_cd") != "0":
                error_msg = response.get("msg1", "Unknown error")
                raise DataProviderError(f"API Error: {error_msg}", response.get("msg_cd"))
            
            # OHLCV 데이터 파싱
            output_list = response["output"]
            ohlcv_list = []
            
            for data in output_list[:limit]:
                try:
                    # 날짜 파싱
                    date_str = data["stck_bsop_date"]
                    date = datetime.strptime(date_str, "%Y%m%d")
                    
                    # 날짜 필터링
                    if start_date and date.date() < start_date.date():
                        continue
                    if end_date and date.date() > end_date.date():
                        continue
                    
                    ohlcv = OHLCV(
                        symbol=symbol,
                        timestamp=date,
                        data_type="ohlcv",
                        source="kiwoom",
                        open_price=self._parse_decimal(data["stck_oprc"]),
                        high_price=self._parse_decimal(data["stck_hgpr"]),
                        low_price=self._parse_decimal(data["stck_lwpr"]),
                        close_price=self._parse_decimal(data["stck_clpr"]),
                        volume=self._parse_int(data["acml_vol"]),
                        trade_value=self._parse_decimal(data["acml_tr_pbmn"]),
                        period=period
                    )
                    
                    ohlcv_list.append(ohlcv)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse OHLCV data: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(ohlcv_list)} OHLCV records for {symbol}")
            return ohlcv_list
            
        except DataProviderError:
            raise
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            raise DataProviderError(f"Failed to get OHLCV: {e}")
    
    async def get_multiple_quotes(self, symbols: List[str]) -> List[Quote]:
        """
        다중 종목 현재가 조회
        
        Args:
            symbols: 종목 코드 리스트
            
        Returns:
            현재가 데이터 리스트
        """
        if not self._connected:
            raise DataProviderError("Provider is not connected")
        
        # 배치 요청 생성
        requests = [
            {
                "api_id": "ka10001",
                "params": {"FID_INPUT_ISCD": symbol}
            }
            for symbol in symbols
        ]
        
        try:
            # 배치 실행
            responses = await self.api_client.batch_request(requests)
            quotes = []
            
            for i, response in enumerate(responses):
                symbol = symbols[i]
                
                try:
                    if response.get("rt_cd") == "0":
                        output = response["output"]
                        
                        quote = Quote(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            data_type="quote",
                            source="kiwoom",
                            price=self._parse_decimal(output["stck_prpr"]),
                            prev_close=self._calculate_prev_close(
                                self._parse_decimal(output["stck_prpr"]),
                                self._parse_decimal(output["prdy_vrss"]),
                                output["prdy_vrss_sign"]
                            ),
                            change=self._parse_decimal(output["prdy_vrss"]),
                            change_rate=self._parse_decimal(output["prdy_ctrt"]),
                            volume=self._parse_int(output["acml_vol"]),
                            trade_value=self._parse_decimal(output["acml_tr_pbmn"]),
                            open_price=self._parse_decimal(output["stck_oprc"]),
                            high_price=self._parse_decimal(output["stck_hgpr"]),
                            low_price=self._parse_decimal(output["stck_lwpr"])
                        )
                        
                        quotes.append(quote)
                    else:
                        logger.warning(f"Failed to get quote for {symbol}: {response.get('msg1')}")
                        
                except Exception as e:
                    logger.warning(f"Failed to parse quote for {symbol}: {e}")
                    continue
            
            return quotes
            
        except Exception as e:
            logger.error(f"Failed to get multiple quotes: {e}")
            raise DataProviderError(f"Failed to get multiple quotes: {e}")
    
    async def _get_daily_ohlcv_continuous(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> AsyncGenerator[List[OHLCV], None]:
        """연속조회를 통한 일봉 데이터 수집"""
        try:
            async for response in self.api_client.continuous_request(
                api_id="ka10002",
                params={
                    "FID_INPUT_ISCD": symbol,
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "1"
                },
                max_pages=10
            ):
                # 응답 파싱
                if response.get("rt_cd") != "0":
                    logger.warning(f"API error in continuous request: {response.get('msg1')}")
                    break
                
                ohlcv_batch = []
                output_list = response.get("output", [])
                
                for data in output_list:
                    try:
                        date_str = data["stck_bsop_date"]
                        date = datetime.strptime(date_str, "%Y%m%d")
                        
                        if date.date() < start_date.date():
                            return  # 시작일 이전이면 중단
                        if date.date() > end_date.date():
                            continue  # 종료일 이후는 건너뛰기
                        
                        ohlcv = OHLCV(
                            symbol=symbol,
                            timestamp=date,
                            data_type="ohlcv",
                            source="kiwoom",
                            open_price=self._parse_decimal(data["stck_oprc"]),
                            high_price=self._parse_decimal(data["stck_hgpr"]),
                            low_price=self._parse_decimal(data["stck_lwpr"]),
                            close_price=self._parse_decimal(data["stck_clpr"]),
                            volume=self._parse_int(data["acml_vol"]),
                            trade_value=self._parse_decimal(data["acml_tr_pbmn"]),
                            period="1D"
                        )
                        
                        ohlcv_batch.append(ohlcv)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse continuous OHLCV data: {e}")
                        continue
                
                if ohlcv_batch:
                    yield ohlcv_batch
                    
        except Exception as e:
            logger.error(f"Error in continuous OHLCV collection: {e}")
            raise DataProviderError(f"Continuous data collection failed: {e}")
    
    def _parse_decimal(self, value: str) -> Decimal:
        """문자열을 Decimal로 변환"""
        try:
            return Decimal(str(value).replace(",", ""))
        except (InvalidOperation, ValueError) as e:
            raise DataProviderError(f"Invalid decimal value: {value}")
    
    def _parse_decimal_optional(self, value: Optional[str]) -> Optional[Decimal]:
        """선택적 Decimal 파싱"""
        if not value:
            return None
        try:
            return self._parse_decimal(value)
        except DataProviderError:
            return None
    
    def _parse_int(self, value: str) -> int:
        """문자열을 int로 변환"""
        try:
            return int(str(value).replace(",", ""))
        except (ValueError, TypeError) as e:
            raise DataProviderError(f"Invalid integer value: {value}")
    
    def _parse_int_optional(self, value: Optional[str]) -> Optional[int]:
        """선택적 int 파싱"""
        if not value:
            return None
        try:
            return self._parse_int(value)
        except DataProviderError:
            return None
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected
    
    def _calculate_prev_close(self, current_price: Decimal, change: Decimal, sign: str) -> Decimal:
        """전일종가 계산"""
        try:
            # 키움 API 부호: 1=상한, 2=상승, 3=보합, 4=하한, 5=하락
            if sign in ["1", "2"]:  # 상승
                return current_price - change
            elif sign in ["4", "5"]:  # 하락
                return current_price + abs(change)
            else:  # 보합
                return current_price
        except Exception:
            return current_price