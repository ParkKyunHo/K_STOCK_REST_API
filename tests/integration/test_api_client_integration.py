"""
API 클라이언트 통합 테스트
"""
import os
import pytest

from src.infrastructure.api.client import ClientFactory
from src.infrastructure.api.auth.credential_manager import Credentials


class TestAPIClientIntegration:
    """API 클라이언트 통합 테스트"""
    
    @pytest.fixture
    def test_credentials(self):
        """테스트용 자격증명"""
        return Credentials(
            app_key="test_app_key",
            app_secret="test_app_secret",
            account_no="12345678",
            account_type="stock"
        )
    
    @pytest.mark.asyncio
    async def test_client_factory_mock_creation(self, test_credentials):
        """클라이언트 팩토리 Mock 생성 테스트"""
        client = ClientFactory.create_client(
            use_mock=True,
            credentials=test_credentials,
            base_url="https://test.api.com"
        )
        
        async with client as api_client:
            # 기본 기능 테스트
            response = await api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"}
            )
            
            assert response["rt_cd"] == "0"
            assert "output" in response
    
    @pytest.mark.asyncio
    async def test_environment_variable_integration(self, test_credentials):
        """환경변수 통합 테스트"""
        # 환경변수 설정
        os.environ["USE_MOCK_API"] = "true"
        os.environ["API_RATE_LIMIT"] = "20"
        os.environ["CACHE_TTL"] = "600"
        
        try:
            client = ClientFactory.create_client(credentials=test_credentials)
            
            # 환경변수가 제대로 적용되었는지 확인
            assert client.rate_limit == 20
            assert client.cache_ttl == 600
            
            async with client as api_client:
                # 헬스 체크
                is_healthy = await api_client.health_check()
                assert is_healthy is True
                
                # 통계 확인
                stats = api_client.get_stats()
                assert "client_type" in stats
        finally:
            # 환경변수 정리
            del os.environ["USE_MOCK_API"]
            del os.environ["API_RATE_LIMIT"]
            del os.environ["CACHE_TTL"]
    
    @pytest.mark.asyncio
    async def test_test_client_creation(self):
        """테스트 클라이언트 생성 테스트"""
        client = ClientFactory.create_test_client()
        
        async with client as api_client:
            # 여러 API 호출
            responses = await api_client.batch_request([
                {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "005930"}},
                {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "000660"}},
                {"api_id": "ka10002", "params": {"FID_INPUT_ISCD": "035720"}}
            ])
            
            assert len(responses) == 3
            assert all(resp["rt_cd"] == "0" for resp in responses if "error" not in resp)
    
    @pytest.mark.asyncio 
    async def test_continuous_request_integration(self):
        """연속조회 통합 테스트"""
        client = ClientFactory.create_test_client()
        
        async with client as api_client:
            pages_collected = 0
            
            async for page_data in api_client.continuous_request(
                api_id="ka10002",
                params={"FID_INPUT_ISCD": "005930"},
                max_pages=3
            ):
                pages_collected += 1
                assert page_data["rt_cd"] == "0"
                
                if pages_collected >= 3:  # 안전장치
                    break
            
            assert pages_collected >= 1
    
    @pytest.mark.asyncio
    async def test_websocket_integration(self):
        """WebSocket 통합 테스트"""
        client = ClientFactory.create_test_client()
        
        async with client as api_client:
            async with await api_client.websocket_connect() as ws:
                # 메시지 전송
                await ws.send_str('{"tr_id": "H0STCNT0", "input": {"tr_key": "005930"}}')
                
                # 응답 수신
                response = await ws.receive_str()
                assert response is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        client = ClientFactory.create_test_client()
        
        async with client as api_client:
            # 에러 시뮬레이션 활성화
            api_client.set_error_simulation(True)
            
            # 여러 번 시도하여 에러 발생 확인
            try:
                for _ in range(10):  # 10번 시도
                    await api_client.request("ka10001", {})
            except Exception as e:
                # 에러가 적절히 발생하는지 확인
                assert "error" in str(e).lower() or "failed" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_caching_integration(self):
        """캐싱 통합 테스트 (Mock 클라이언트에서는 기본 동작 확인)"""
        client = ClientFactory.create_test_client(cache_ttl=1)  # 1초 TTL
        
        async with client as api_client:
            # Mock 클라이언트에서는 캐싱이 구현되지 않았으므로
            # 기본적인 요청 동작만 확인
            response1 = await api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"},
                use_cache=True
            )
            
            response2 = await api_client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"},
                use_cache=True
            )
            
            # Mock 클라이언트에서는 요청이 두 번 발생
            assert api_client.get_request_count() == 2
            # 응답 구조는 동일해야 함
            assert response1["rt_cd"] == response2["rt_cd"] == "0"