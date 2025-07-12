"""
키움증권 API 클라이언트 테스트
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientResponseError

from src.infrastructure.api.client.kiwoom_api_client import (
    KiwoomAPIClient,
    APIError,
    RateLimitError,
    CacheError
)
from src.infrastructure.api.auth.credential_manager import Credentials


class TestKiwoomAPIClient:
    """KiwoomAPIClient 테스트"""
    
    @pytest.fixture
    def credentials(self):
        """테스트용 자격증명"""
        return Credentials(
            app_key="test_app_key",
            app_secret="test_app_secret",
            account_no="12345678",
            account_type="stock"
        )
    
    @pytest.fixture
    def api_client(self, credentials):
        """API 클라이언트 픽스처"""
        return KiwoomAPIClient(
            base_url="https://api.test.com",
            credentials=credentials,
            rate_limit=10,  # 10 req/sec
            cache_ttl=300,  # 5분
            max_retries=3,
            timeout=30
        )
    
    @pytest.fixture
    def mock_response_data(self):
        """모의 응답 데이터"""
        return {
            "rt_cd": "0",
            "msg_cd": "000000",
            "msg1": "SUCCESS",
            "output": {
                "hts_kor_isnm": "삼성전자",
                "stck_prpr": "70000",
                "prdy_vrss": "1000",
                "prdy_vrss_sign": "2"
            }
        }
    
    def test_api_client_initialization(self, credentials):
        """API 클라이언트 초기화 테스트"""
        client = KiwoomAPIClient(
            base_url="https://api.kiwoom.com",
            credentials=credentials,
            rate_limit=20,
            cache_ttl=600,
            max_retries=5,
            timeout=60
        )
        
        assert client.base_url == "https://api.kiwoom.com"
        assert client.rate_limit == 20
        assert client.cache_ttl == 600
        assert client.max_retries == 5
        assert client.timeout == 60
        assert client._request_times == []
        assert client._cache == {}
    
    @pytest.mark.asyncio
    async def test_api_client_context_manager(self, api_client):
        """컨텍스트 매니저 테스트"""
        async with api_client as client:
            assert client is not None
            assert hasattr(client, '_session')
    
    @pytest.mark.asyncio
    async def test_successful_api_request(self, api_client, mock_response_data):
        """성공적인 API 요청 테스트"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            response = await api_client.request(
                api_id="ka10001",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"}
            )
            
            assert response["rt_cd"] == "0"
            assert response["output"]["hts_kor_isnm"] == "삼성전자"
    
    @pytest.mark.asyncio
    async def test_api_request_with_headers(self, api_client, mock_response_data):
        """헤더가 포함된 API 요청 테스트"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response) as mock_request:
            await api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"},
                headers={"tr_id": "FHKST01010100"}
            )
            
            # 호출된 헤더 확인
            call_args = mock_request.call_args
            headers = call_args[1]["headers"]
            
            assert "authorization" in headers
            assert "api-id" in headers
            assert headers["api-id"] == "ka10001"
            assert headers["tr_id"] == "FHKST01010100"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_client):
        """Rate Limiting 테스트"""
        # Rate limit을 낮게 설정 (2 req/sec)
        api_client.rate_limit = 2
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"rt_cd": "0"}
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            start_time = time.time()
            
            # 3번 요청
            await api_client.request("ka10001", {})
            await api_client.request("ka10001", {})
            await api_client.request("ka10001", {})
            
            elapsed = time.time() - start_time
            
            # Rate limiting으로 인해 최소 1초는 걸려야 함 (3개 요청, 2 req/sec)
            assert elapsed >= 1.0
    
    @pytest.mark.asyncio
    async def test_caching_mechanism(self, api_client, mock_response_data):
        """캐싱 메커니즘 테스트"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response) as mock_request:
            # 첫 번째 요청 (캐시 없음)
            response1 = await api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"},
                use_cache=True
            )
            
            # 두 번째 요청 (캐시 사용)
            response2 = await api_client.request(
                api_id="ka10001", 
                params={"FID_INPUT_ISCD": "005930"},
                use_cache=True
            )
            
            # HTTP 요청은 한 번만 발생해야 함
            assert mock_request.call_count == 1
            assert response1 == response2
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, api_client, mock_response_data):
        """캐시 만료 테스트"""
        # 짧은 TTL 설정
        api_client.cache_ttl = 0.1  # 100ms
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response) as mock_request:
            # 첫 번째 요청
            await api_client.request("ka10001", {"test": "1"}, use_cache=True)
            
            # 캐시 만료 대기
            await asyncio.sleep(0.2)
            
            # 두 번째 요청 (캐시 만료됨)
            await api_client.request("ka10001", {"test": "1"}, use_cache=True)
            
            # HTTP 요청이 두 번 발생해야 함
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, api_client):
        """재시도 메커니즘 테스트"""
        # 처음 두 번은 실패, 세 번째는 성공
        side_effects = [
            ClientResponseError(Mock(), Mock(), status=500),
            ClientResponseError(Mock(), Mock(), status=502),
            AsyncMock(status=200, json=AsyncMock(return_value={"rt_cd": "0"}))
        ]
        
        with patch.object(api_client, '_make_http_request', side_effect=side_effects):
            response = await api_client.request("ka10001", {})
            
            assert response["rt_cd"] == "0"
    
    @pytest.mark.asyncio 
    async def test_retry_exhaustion(self, api_client):
        """재시도 한계 초과 테스트"""
        # 모든 시도가 실패
        with patch.object(api_client, '_make_http_request', 
                         side_effect=ClientResponseError(Mock(), Mock(), status=500)):
            
            with pytest.raises(APIError) as exc_info:
                await api_client.request("ka10001", {})
            
            assert "Max retries exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_api_error_response(self, api_client):
        """API 오류 응답 테스트"""
        error_response = {
            "rt_cd": "1", 
            "msg_cd": "000001",
            "msg1": "잘못된 종목코드입니다."
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = error_response
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                await api_client.request("ka10001", {"FID_INPUT_ISCD": "invalid"})
            
            assert "잘못된 종목코드입니다" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_continuous_request_support(self, api_client):
        """연속조회 지원 테스트"""
        # 첫 번째 응답 (다음 키 포함)
        first_response = {
            "rt_cd": "0",
            "msg_cd": "000000", 
            "msg1": "SUCCESS",
            "output": [{"data": "page1"}],
            "ctx_area_fk100": "next_key_123",
            "ctx_area_nk100": "next_key_456"
        }
        
        # 두 번째 응답 (마지막 페이지)
        second_response = {
            "rt_cd": "0",
            "msg_cd": "000000",
            "msg1": "SUCCESS", 
            "output": [{"data": "page2"}],
            "ctx_area_fk100": "",
            "ctx_area_nk100": ""
        }
        
        mock_responses = [
            AsyncMock(status=200, json=AsyncMock(return_value=first_response)),
            AsyncMock(status=200, json=AsyncMock(return_value=second_response))
        ]
        
        with patch.object(api_client, '_make_http_request', side_effect=mock_responses):
            all_data = []
            
            async for page_data in api_client.continuous_request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"}
            ):
                all_data.extend(page_data["output"])
            
            assert len(all_data) == 2
            assert all_data[0]["data"] == "page1"
            assert all_data[1]["data"] == "page2"
    
    @pytest.mark.asyncio
    async def test_batch_request(self, api_client):
        """배치 요청 테스트"""
        requests = [
            {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "005930"}},
            {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "000660"}},
            {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "035720"}}
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"rt_cd": "0", "output": {"price": "100"}}
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            responses = await api_client.batch_request(requests, max_concurrent=2)
            
            assert len(responses) == 3
            assert all(resp["rt_cd"] == "0" for resp in responses)
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, api_client):
        """WebSocket 연결 테스트"""
        mock_websocket = AsyncMock()
        mock_websocket.send_str = AsyncMock()
        mock_websocket.receive_str = AsyncMock(return_value='{"rt_cd": "0"}')
        
        with patch('aiohttp.ClientSession.ws_connect', return_value=mock_websocket):
            async with api_client.websocket_connect() as ws:
                await ws.send_str('{"tr_id": "H0STCNT0"}')
                message = await ws.receive_str()
                
                assert json.loads(message)["rt_cd"] == "0"
    
    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """헬스 체크 테스트"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"rt_cd": "0"}
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            is_healthy = await api_client.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, api_client):
        """헬스 체크 실패 테스트"""
        with patch.object(api_client, '_make_http_request', 
                         side_effect=Exception("Connection failed")):
            is_healthy = await api_client.health_check()
            assert is_healthy is False
    
    def test_cache_key_generation(self, api_client):
        """캐시 키 생성 테스트"""
        key1 = api_client._generate_cache_key("ka10001", {"a": "1", "b": "2"})
        key2 = api_client._generate_cache_key("ka10001", {"b": "2", "a": "1"})
        key3 = api_client._generate_cache_key("ka10002", {"a": "1", "b": "2"})
        
        # 같은 API와 파라미터는 같은 키
        assert key1 == key2
        # 다른 API는 다른 키
        assert key1 != key3
    
    def test_get_api_headers(self, api_client):
        """API 헤더 생성 테스트"""
        headers = api_client._get_api_headers(
            api_id="ka10001",
            tr_id="FHKST01010100",
            cont_yn="N"
        )
        
        assert headers["content-type"] == "application/json;charset=UTF-8"
        assert headers["api-id"] == "ka10001"
        assert headers["tr_id"] == "FHKST01010100"
        assert headers["cont-yn"] == "N"
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, api_client):
        """Rate limit 리셋 테스트"""
        # 1초 윈도우에 2개 요청 제한
        api_client.rate_limit = 2
        
        # 첫 번째 윈도우에서 2개 요청
        api_client._request_times = [time.time(), time.time()]
        
        # 1초 대기
        await asyncio.sleep(1.1)
        
        # 새로운 요청이 가능해야 함
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"rt_cd": "0"}
        
        with patch.object(api_client, '_make_http_request', return_value=mock_response):
            response = await api_client.request("ka10001", {})
            assert response["rt_cd"] == "0"
    
    def test_error_classes(self):
        """에러 클래스 테스트"""
        api_error = APIError("API request failed", "000001")
        assert str(api_error) == "API request failed"
        assert api_error.error_code == "000001"
        
        rate_limit_error = RateLimitError("Rate limit exceeded")
        assert "Rate limit exceeded" in str(rate_limit_error)
        
        cache_error = CacheError("Cache operation failed")
        assert "Cache operation failed" in str(cache_error)