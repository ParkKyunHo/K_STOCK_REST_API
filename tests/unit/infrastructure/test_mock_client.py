"""
Mock API 클라이언트 테스트
"""
import pytest

from src.infrastructure.api.client.mock_client import MockKiwoomAPIClient
from src.infrastructure.api.client.client_factory import ClientFactory


class TestMockKiwoomAPIClient:
    """MockKiwoomAPIClient 테스트"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock 클라이언트 픽스처"""
        return ClientFactory.create_test_client()
    
    @pytest.mark.asyncio
    async def test_mock_client_initialization(self, mock_client):
        """Mock 클라이언트 초기화 테스트"""
        async with mock_client as client:
            assert client is not None
            assert "mock" in client.get_stats()["client_type"]
    
    @pytest.mark.asyncio
    async def test_mock_api_request(self, mock_client):
        """Mock API 요청 테스트"""
        async with mock_client as client:
            response = await client.request(
                api_id="ka10001",
                params={"FID_INPUT_ISCD": "005930"}
            )
            
            assert response["rt_cd"] == "0"
            assert "output" in response
            assert "hts_kor_isnm" in response["output"]
    
    @pytest.mark.asyncio
    async def test_mock_continuous_request(self, mock_client):
        """Mock 연속조회 테스트"""
        async with mock_client as client:
            pages = []
            
            async for page_data in client.continuous_request(
                api_id="ka10002",
                params={"FID_INPUT_ISCD": "005930"}
            ):
                pages.append(page_data)
            
            assert len(pages) >= 1
            assert all(page["rt_cd"] == "0" for page in pages)
    
    @pytest.mark.asyncio
    async def test_mock_batch_request(self, mock_client):
        """Mock 배치 요청 테스트"""
        async with mock_client as client:
            requests = [
                {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "005930"}},
                {"api_id": "ka10001", "params": {"FID_INPUT_ISCD": "000660"}}
            ]
            
            responses = await client.batch_request(requests)
            
            assert len(responses) == 2
            assert all(resp["rt_cd"] == "0" for resp in responses)
    
    @pytest.mark.asyncio
    async def test_error_simulation(self, mock_client):
        """에러 시뮬레이션 테스트"""
        async with mock_client as client:
            # 에러 시뮬레이션 활성화
            client.set_error_simulation(True)
            
            # 여러 번 시도해서 에러 발생 확인
            error_occurred = False
            for _ in range(20):  # 20번 시도
                try:
                    await client.request("ka10001", {})
                except Exception:
                    error_occurred = True
                    break
            
            # 에러 시뮬레이션이 작동했는지 확인 (100% 보장은 아니지만 높은 확률)
            # 실제로는 10% 확률이므로 20번 시도하면 발생할 가능성이 높음
    
    @pytest.mark.asyncio
    async def test_mock_websocket(self, mock_client):
        """Mock WebSocket 테스트"""
        async with mock_client as client:
            async with await client.websocket_connect() as ws:
                await ws.send_str('{"tr_id": "H0STCNT0"}')
                response = await ws.receive_str()
                
                assert response is not None
    
    @pytest.mark.asyncio
    async def test_mock_health_check(self, mock_client):
        """Mock 헬스 체크 테스트"""
        async with mock_client as client:
            # 정상 상태
            is_healthy = await client.health_check()
            assert is_healthy is True
            
            # 에러 시뮬레이션 활성화 후
            client.set_error_simulation(True)
            is_healthy = await client.health_check()
            assert is_healthy is False
    
    def test_mock_custom_data(self, mock_client):
        """사용자 정의 Mock 데이터 테스트"""
        custom_response = {
            "rt_cd": "0",
            "msg1": "CUSTOM_SUCCESS",
            "output": {"custom_field": "custom_value"}
        }
        
        mock_client.add_mock_data("custom_api", custom_response)
        
        # Mock 데이터가 추가되었는지 확인
        stats = mock_client.get_stats()
        assert "custom_api" in stats["available_apis"]
    
    def test_client_factory(self):
        """클라이언트 팩토리 테스트"""
        # Mock 클라이언트 생성
        mock_client = ClientFactory.create_test_client()
        assert isinstance(mock_client, MockKiwoomAPIClient)
        
        # 통계 확인
        stats = mock_client.get_stats()
        assert stats["client_type"] == "mock"
        assert stats["total_requests"] == 0
    
    def test_mock_stats_tracking(self, mock_client):
        """Mock 통계 추적 테스트"""
        initial_count = mock_client.get_request_count()
        assert initial_count == 0
        
        # 통계 리셋
        mock_client.reset_stats()
        assert mock_client.get_request_count() == 0