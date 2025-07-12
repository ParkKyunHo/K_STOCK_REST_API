"""
인증 서비스 테스트
"""
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.api.auth.authentication_service import (
    AuthenticationService,
    AuthenticationError
)
from src.infrastructure.api.auth.credential_manager import Credentials


class TestAuthenticationService:
    """AuthenticationService 테스트"""
    
    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def test_credentials(self):
        """테스트용 자격증명"""
        return Credentials(
            app_key="test_app_key",
            app_secret="test_app_secret",
            account_no="12345678",
            account_type="stock"
        )
    
    @pytest.fixture
    def mock_token_response(self):
        """모의 토큰 응답"""
        return {
            "access_token": "test_access_token_12345",
            "token_type": "Bearer",
            "expires_in": 7200,
            "expires_dt": (datetime.now() + timedelta(hours=2)).isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_authentication_service_initialization(self, temp_dir):
        """인증 서비스 초기화 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        assert service.base_url == "https://api.test.com"
        assert service.credential_manager is not None
        assert service._oauth_manager is None
    
    @pytest.mark.asyncio
    async def test_set_credentials(self, temp_dir, test_credentials):
        """자격증명 설정 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 자격증명 설정
        await service.set_credentials(test_credentials)
        
        # 자격증명이 저장되었는지 확인
        loaded_creds = service.credential_manager.load_credentials()
        assert loaded_creds is not None
        assert loaded_creds.app_key == test_credentials.app_key
        
        # OAuth 매니저가 생성되었는지 확인
        assert service._oauth_manager is not None
    
    @pytest.mark.asyncio
    async def test_get_access_token(self, temp_dir, test_credentials, mock_token_response):
        """액세스 토큰 획득 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 자격증명 설정
        await service.set_credentials(test_credentials)
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            
            token = await service.get_access_token()
            
            assert token == "test_access_token_12345"
    
    @pytest.mark.asyncio
    async def test_get_authenticated_headers(self, temp_dir, test_credentials, mock_token_response):
        """인증 헤더 생성 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service.set_credentials(test_credentials)
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            
            headers = await service.get_authenticated_headers()
            
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_access_token_12345"
            assert "content-type" in headers
    
    @pytest.mark.asyncio
    async def test_auto_initialize_from_storage(self, temp_dir, test_credentials):
        """저장된 자격증명 자동 로드 테스트"""
        # 먼저 자격증명을 저장
        service1 = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        await service1.set_credentials(test_credentials)
        
        # 새 서비스 인스턴스에서 자동 로드
        service2 = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service2.initialize()
        
        # OAuth 매니저가 자동으로 생성되었는지 확인
        assert service2._oauth_manager is not None
        assert service2.is_authenticated()
    
    @pytest.mark.asyncio
    async def test_is_authenticated(self, temp_dir, test_credentials):
        """인증 상태 확인 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 초기에는 인증되지 않음
        assert not service.is_authenticated()
        
        # 자격증명 설정 후 인증됨
        await service.set_credentials(test_credentials)
        assert service.is_authenticated()
    
    @pytest.mark.asyncio
    async def test_clear_authentication(self, temp_dir, test_credentials):
        """인증 정보 삭제 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 자격증명 설정
        await service.set_credentials(test_credentials)
        assert service.is_authenticated()
        
        # 인증 정보 삭제
        await service.clear_authentication()
        
        assert not service.is_authenticated()
        assert service._oauth_manager is None
        
        # 저장된 자격증명도 삭제되었는지 확인
        loaded_creds = service.credential_manager.load_credentials()
        assert loaded_creds is None
    
    @pytest.mark.asyncio
    async def test_token_refresh_automatically(self, temp_dir, test_credentials):
        """토큰 자동 갱신 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service.set_credentials(test_credentials)
        
        # 초기 토큰 발급
        initial_token_response = {
            "access_token": "initial_token",
            "token_type": "Bearer",
            "expires_in": 300  # 5분
        }
        
        # 갱신된 토큰 응답
        refreshed_token_response = {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 7200
        }
        
        responses = [initial_token_response, refreshed_token_response]
        response_iter = iter(responses)
        
        async def mock_response(*args, **kwargs):
            mock_resp = AsyncMock()
            mock_resp.json = AsyncMock(return_value=next(response_iter))
            mock_resp.status = 200
            return mock_resp
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__ = mock_response
            
            # 첫 번째 토큰 획득
            token1 = await service.get_access_token()
            assert token1 == "initial_token"
            
            # 토큰 만료 시뮬레이션
            service._oauth_manager.token_info.expires_at = datetime.now() - timedelta(minutes=1)
            
            # 두 번째 호출에서 자동 갱신
            token2 = await service.get_access_token()
            assert token2 == "refreshed_token"
    
    @pytest.mark.asyncio
    async def test_error_handling_no_credentials(self, temp_dir):
        """자격증명 없음 에러 처리 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 자격증명 없이 토큰 요청
        with pytest.raises(AuthenticationError) as exc_info:
            await service.get_access_token()
        
        assert "credentials" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_credentials(self, temp_dir):
        """잘못된 자격증명 에러 처리 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 잘못된 자격증명 설정
        invalid_creds = Credentials(
            app_key="invalid_key",
            app_secret="invalid_secret",
            account_no="12345678"
        )
        await service.set_credentials(invalid_creds)
        
        # Mock 401 응답
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception):
                await service.get_access_token()
    
    @pytest.mark.asyncio
    async def test_update_credentials(self, temp_dir, test_credentials):
        """자격증명 업데이트 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        # 초기 자격증명 설정
        await service.set_credentials(test_credentials)
        
        # 새로운 자격증명
        new_credentials = Credentials(
            app_key="new_app_key",
            app_secret="new_app_secret",
            account_no="87654321",
            account_type="futures"
        )
        
        # 자격증명 업데이트
        await service.set_credentials(new_credentials)
        
        # 새로운 OAuth 매니저가 생성되었는지 확인
        assert service._oauth_manager.app_key == "new_app_key"
        assert service._oauth_manager.app_secret == "new_app_secret"
        
        # 저장소에도 업데이트되었는지 확인
        loaded_creds = service.credential_manager.load_credentials()
        assert loaded_creds.app_key == "new_app_key"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, temp_dir, test_credentials):
        """컨텍스트 매니저 테스트"""
        async with AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        ) as service:
            await service.set_credentials(test_credentials)
            assert service.is_authenticated()
        
        # 컨텍스트 종료 후 정리되었는지 확인은 구현에 따라 다름
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, temp_dir, test_credentials):
        """계좌 정보 조회 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service.set_credentials(test_credentials)
        
        account_info = await service.get_account_info()
        
        assert account_info["account_no"] == test_credentials.account_no
        assert account_info["account_type"] == test_credentials.account_type
        assert "app_key" not in account_info  # 보안상 숨김
        assert "app_secret" not in account_info
    
    @pytest.mark.asyncio
    async def test_health_check(self, temp_dir, test_credentials, mock_token_response):
        """헬스 체크 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service.set_credentials(test_credentials)
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await service.health_check()
            
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, temp_dir, test_credentials):
        """헬스 체크 실패 테스트"""
        service = AuthenticationService(
            base_url="https://api.test.com",
            storage_path=temp_dir
        )
        
        await service.set_credentials(test_credentials)
        
        # Mock 실패 응답
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        
        with patch('src.infrastructure.api.auth.oauth2_manager.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await service.health_check()
            
            assert is_healthy is False