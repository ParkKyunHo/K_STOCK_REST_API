"""
키움증권 마켓 데이터 제공자 테스트
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.data.kiwoom_market_data_provider import (
    KiwoomMarketDataProvider,
    DataProviderError
)
from src.core.models.market_data import Quote, OHLCV
from src.infrastructure.api.client import ClientFactory
from src.infrastructure.api.auth.credential_manager import Credentials


class TestKiwoomMarketDataProvider:
    """KiwoomMarketDataProvider 테스트"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock API 클라이언트"""
        return ClientFactory.create_test_client()
    
    @pytest.fixture
    def provider(self, mock_client):
        """마켓 데이터 제공자"""
        return KiwoomMarketDataProvider(api_client=mock_client)
    
    @pytest.fixture
    def mock_quote_response(self):
        """현재가 API 응답 Mock"""
        return {
            "rt_cd": "0",
            "msg_cd": "000000",
            "msg1": "SUCCESS",
            "output": {
                "hts_kor_isnm": "삼성전자",
                "stck_prpr": "70000",          # 현재가
                "prdy_vrss": "1000",           # 전일대비
                "prdy_vrss_sign": "2",         # 부호
                "prdy_ctrt": "1.45",           # 전일대비율
                "stck_oprc": "69500",          # 시가
                "stck_hgpr": "70500",          # 고가
                "stck_lwpr": "69000",          # 저가
                "acml_vol": "1000000",         # 누적거래량
                "acml_tr_pbmn": "70000000000", # 누적거래대금
                "hts_avls": "4200000000000",   # 시가총액
                "lstn_stcn": "5969782550"      # 상장주식수
            }
        }
    
    @pytest.fixture
    def mock_ohlcv_response(self):
        """일봉 API 응답 Mock"""
        return {
            "rt_cd": "0",
            "msg_cd": "000000",
            "msg1": "SUCCESS",
            "output": [
                {
                    "stck_bsop_date": "20231201",
                    "stck_clpr": "70000",      # 종가
                    "stck_oprc": "69500",      # 시가
                    "stck_hgpr": "70500",      # 고가
                    "stck_lwpr": "69000",      # 저가
                    "acml_vol": "1000000",     # 거래량
                    "acml_tr_pbmn": "70000000000"  # 거래대금
                },
                {
                    "stck_bsop_date": "20231130",
                    "stck_clpr": "69000",
                    "stck_oprc": "68500",
                    "stck_hgpr": "69500",
                    "stck_lwpr": "68000",
                    "acml_vol": "1200000",
                    "acml_tr_pbmn": "82800000000"
                }
            ],
            "ctx_area_fk100": "",
            "ctx_area_nk100": ""
        }
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, mock_client):
        """제공자 초기화 테스트"""
        provider = KiwoomMarketDataProvider(api_client=mock_client)
        
        assert provider.api_client is not None
        assert not provider.is_connected()
        assert provider.subscribed_symbols == set()
    
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, provider):
        """연결 및 해제 테스트"""
        # 연결
        connected = await provider.connect()
        assert connected is True
        assert provider.is_connected() is True
        
        # 해제
        await provider.disconnect()
        assert provider.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_get_quote(self, provider, mock_quote_response):
        """현재가 조회 테스트"""
        await provider.connect()
        
        # Mock API 응답 설정
        with patch.object(provider.api_client, 'request', return_value=mock_quote_response):
            quote = await provider.get_quote("005930")
            
            assert isinstance(quote, Quote)
            assert quote.symbol == "005930"
            assert quote.price == Decimal("70000")
            assert quote.prev_close == Decimal("69000")
            assert quote.change == Decimal("1000")
            assert quote.change_rate == Decimal("1.45")
            assert quote.volume == 1000000
            assert quote.data_type == "quote"
            assert quote.source == "kiwoom"
    
    @pytest.mark.asyncio
    async def test_get_ohlcv_daily(self, provider, mock_ohlcv_response):
        """일봉 데이터 조회 테스트"""
        await provider.connect()
        
        # Mock API 응답 설정
        with patch.object(provider.api_client, 'request', return_value=mock_ohlcv_response):
            ohlcv_list = await provider.get_ohlcv(
                symbol="005930",
                period="1D",
                start_date=datetime(2023, 11, 30),
                end_date=datetime(2023, 12, 1)
            )
            
            assert len(ohlcv_list) == 2
            
            # 첫 번째 데이터 (최신)
            first_ohlcv = ohlcv_list[0]
            assert isinstance(first_ohlcv, OHLCV)
            assert first_ohlcv.symbol == "005930"
            assert first_ohlcv.close_price == Decimal("70000")
            assert first_ohlcv.open_price == Decimal("69500")
            assert first_ohlcv.high_price == Decimal("70500")
            assert first_ohlcv.low_price == Decimal("69000")
            assert first_ohlcv.volume == 1000000
            assert first_ohlcv.period == "1D"
            assert first_ohlcv.timestamp.date() == datetime(2023, 12, 1).date()
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, provider):
        """구독/구독해제 테스트"""
        await provider.connect()
        
        # 구독
        subscribed = await provider.subscribe(["005930", "000660"], "quote")
        assert subscribed is True
        assert "005930" in provider.subscribed_symbols
        assert "000660" in provider.subscribed_symbols
        
        # 구독 해제
        unsubscribed = await provider.unsubscribe(["005930"])
        assert unsubscribed is True
        assert "005930" not in provider.subscribed_symbols
        assert "000660" in provider.subscribed_symbols
    
    @pytest.mark.asyncio
    async def test_get_latest_data_cache(self, provider, mock_quote_response):
        """최신 데이터 캐시 테스트"""
        await provider.connect()
        
        # 첫 번째 요청
        with patch.object(provider.api_client, 'request', return_value=mock_quote_response):
            data_point1 = await provider.get_latest_data("005930", "quote")
            assert data_point1 is not None
            assert isinstance(data_point1.data, Quote)
            assert data_point1.data.price == Decimal("70000")
        
        # 캐시된 데이터 조회
        data_point2 = await provider.get_latest_data("005930", "quote")
        assert data_point2 is not None
        assert data_point1.timestamp == data_point2.timestamp  # 같은 데이터
    
    @pytest.mark.asyncio
    async def test_error_handling_api_error(self, provider):
        """API 에러 처리 테스트"""
        await provider.connect()
        
        # API 에러 응답
        error_response = {
            "rt_cd": "1",
            "msg_cd": "000001",
            "msg1": "잘못된 종목코드입니다."
        }
        
        with patch.object(provider.api_client, 'request', return_value=error_response):
            with pytest.raises(DataProviderError) as exc_info:
                await provider.get_quote("INVALID")
            
            assert "잘못된 종목코드" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_handling_not_connected(self, provider):
        """연결되지 않은 상태 에러 테스트"""
        # 연결하지 않은 상태에서 데이터 요청
        with pytest.raises(DataProviderError) as exc_info:
            await provider.get_quote("005930")
        
        assert "not connected" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_historical_data_pagination(self, provider):
        """대용량 과거 데이터 페이징 테스트"""
        await provider.connect()
        
        # 첫 번째 페이지
        page1_response = {
            "rt_cd": "0", 
            "msg_cd": "000000",
            "msg1": "SUCCESS",
            "output": [{
                "stck_bsop_date": "20231201",
                "stck_oprc": "70000", 
                "stck_hgpr": "71000",
                "stck_lwpr": "69000", 
                "stck_clpr": "70500",
                "acml_vol": "1000000",
                "acml_tr_pbmn": "70500000000"
            } for i in range(100)],
            "ctx_area_fk100": "next_key_123",
            "ctx_area_nk100": "next_key_456"
        }
        
        # 두 번째 페이지 (마지막)
        page2_response = {
            "rt_cd": "0",
            "msg_cd": "000000", 
            "msg1": "SUCCESS",
            "output": [{
                "stck_bsop_date": "20231130",
                "stck_oprc": "69500",
                "stck_hgpr": "70000", 
                "stck_lwpr": "68500",
                "stck_clpr": "69800",
                "acml_vol": "1200000",
                "acml_tr_pbmn": "83760000000"
            } for i in range(50)],
            "ctx_area_fk100": "",
            "ctx_area_nk100": ""
        }
        
        responses = [page1_response, page2_response]
        response_iter = iter(responses)
        
        with patch.object(provider.api_client, 'continuous_request') as mock_continuous:
            async def mock_generator(*args, **kwargs):
                for response in responses:
                    yield response
            
            mock_continuous.return_value = mock_generator()
            
            all_data = []
            start_date = datetime(2023, 7, 1)
            end_date = datetime(2023, 12, 31)
            async for data_batch in provider.get_historical_data("005930", "1D", start_date, end_date):
                all_data.extend(data_batch)
            
            # 전체 150개 데이터 수집
            assert len(all_data) == 150
    
    @pytest.mark.asyncio
    async def test_data_validation(self, provider):
        """데이터 유효성 검증 테스트"""
        await provider.connect()
        
        # 잘못된 응답 데이터
        invalid_response = {
            "rt_cd": "0",
            "msg_cd": "000000",
            "msg1": "SUCCESS",
            "output": {
                "hts_kor_isnm": "삼성전자",
                "stck_prpr": "INVALID_PRICE",  # 잘못된 가격
                "prdy_vrss": "1000",
                "prdy_vrss_sign": "2"
            }
        }
        
        with patch.object(provider.api_client, 'request', return_value=invalid_response):
            with pytest.raises(DataProviderError) as exc_info:
                await provider.get_quote("005930")
            
            assert "invalid" in str(exc_info.value).lower() or "conversion" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_multiple_quotes(self, provider, mock_quote_response):
        """다중 종목 현재가 조회 테스트"""
        await provider.connect()
        
        symbols = ["005930", "000660", "035720"]
        
        with patch.object(provider.api_client, 'batch_request') as mock_batch:
            # 각 종목에 대한 응답 생성
            batch_responses = []
            for i, symbol in enumerate(symbols):
                response = mock_quote_response.copy()
                response["output"] = response["output"].copy()  # output도 깊은 복사
                response["output"]["stck_prpr"] = str(70000 + i * 1000)
                batch_responses.append(response)
            
            mock_batch.return_value = batch_responses
            
            quotes = await provider.get_multiple_quotes(symbols)
            
            assert len(quotes) == 3
            for i, quote in enumerate(quotes):
                assert quote.symbol == symbols[i]
                assert quote.price == Decimal(str(70000 + i * 1000))
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, provider, mock_quote_response):
        """캐시 만료 테스트"""
        # 짧은 캐시 TTL로 설정
        provider.cache_ttl = 0.1  # 100ms
        await provider.connect()
        
        with patch.object(provider.api_client, 'request', return_value=mock_quote_response) as mock_request:
            # 첫 번째 요청
            quote1 = await provider.get_quote("005930")
            assert mock_request.call_count == 1
            
            # 두 번째 요청 (캐시된 데이터 없음 - 다른 API 호출)
            quote2 = await provider.get_quote("005930")
            assert mock_request.call_count == 2  # get_quote는 캐시를 사용하지 않음
            
            # get_latest_data를 사용해서 캐시 테스트
            data_point1 = await provider.get_latest_data("005930", "quote")
            assert mock_request.call_count == 3  # get_quote + get_latest_data
            
            # 캐시된 데이터 조회 (추가 API 호출 없음)
            data_point2 = await provider.get_latest_data("005930", "quote")
            assert mock_request.call_count == 3  # 캐시 사용으로 호출 수 유지
            
            # 캐시 만료 대기
            import asyncio
            await asyncio.sleep(0.2)
            
            # 캐시 만료 후 새 요청
            data_point3 = await provider.get_latest_data("005930", "quote")
            assert mock_request.call_count == 4  # 캐시 만료로 새 호출
    
    def test_data_provider_error(self):
        """DataProviderError 테스트"""
        error = DataProviderError("Test error", "TEST001")
        assert str(error) == "Test error"
        assert error.error_code == "TEST001"