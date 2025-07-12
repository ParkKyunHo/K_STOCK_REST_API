"""
인증 시스템 통합 테스트
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.api.auth.credential_manager import (
    CredentialManager,
    Credentials,
)
from src.infrastructure.api.auth.oauth2_manager import OAuth2Manager


class TestAuthenticationIntegration:
    """인증 시스템 통합 테스트"""
    
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
    async def test_credential_storage_and_oauth_flow(self, temp_dir, test_credentials, mock_token_response):
        """자격증명 저장 및 OAuth 플로우 통합 테스트"""
        # 1. 자격증명 저장
        cred_manager = CredentialManager(storage_path=temp_dir)
        cred_manager.save_credentials(test_credentials)
        
        # 2. 자격증명 로드
        loaded_creds = cred_manager.load_credentials()
        assert loaded_creds is not None
        
        # 3. OAuth 매니저 생성
        oauth_manager = OAuth2Manager(
            app_key=loaded_creds.app_key,
            app_secret=loaded_creds.app_secret,
            base_url="https://api.test.com"
        )
        
        # 4. 토큰 발급 (Mock)
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token = await oauth_manager.get_access_token()
            
            assert token == "test_access_token_12345"
            assert oauth_manager.token_info is not None
    
    @pytest.mark.asyncio
    async def test_environment_variable_fallback(self, temp_dir, mock_token_response):
        """환경변수 폴백 통합 테스트"""
        # 환경변수 설정
        env_vars = {
            "KIWOOM_APP_KEY": "env_app_key",
            "KIWOOM_APP_SECRET": "env_app_secret",
            "KIWOOM_ACCOUNT_NO": "87654321"
        }
        
        with patch.dict(os.environ, env_vars):
            # 자격증명 매니저 (파일 없음)
            cred_manager = CredentialManager(storage_path=temp_dir)
            loaded_creds = cred_manager.load_credentials()
            
            assert loaded_creds is not None
            assert loaded_creds.app_key == "env_app_key"
            
            # OAuth 매니저로 인증
            oauth_manager = OAuth2Manager(
                app_key=loaded_creds.app_key,
                app_secret=loaded_creds.app_secret,
                base_url="https://api.test.com"
            )
            
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=mock_token_response)
            mock_response.status = 200
            
            with patch('aiohttp.ClientSession') as mock_session:
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                token = await oauth_manager.get_access_token()
                assert token is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, temp_dir, test_credentials, mock_token_response):
        """동시 인증 요청 처리 테스트"""
        # 자격증명 저장
        cred_manager = CredentialManager(storage_path=temp_dir)
        cred_manager.save_credentials(test_credentials)
        
        # 여러 OAuth 매니저 인스턴스
        oauth_managers = []
        for _ in range(3):
            loaded_creds = cred_manager.load_credentials()
            oauth_manager = OAuth2Manager(
                app_key=loaded_creds.app_key,
                app_secret=loaded_creds.app_secret,
                base_url="https://api.test.com"
            )
            oauth_managers.append(oauth_manager)
        
        # Mock 설정
        call_count = 0
        
        async def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=mock_token_response)
            mock_response.status = 200
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_context = AsyncMock()
            mock_context.__aenter__ = count_calls
            mock_session.return_value.__aenter__.return_value.post.return_value = mock_context
            
            # 동시 토큰 요청
            tasks = [manager.get_access_token() for manager in oauth_managers]
            tokens = await asyncio.gather(*tasks)
            
            # 모든 매니저가 토큰을 받았는지 확인
            assert all(token is not None for token in tokens)
            # 각 매니저가 독립적으로 토큰을 요청했는지 확인
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_credential_update_flow(self, temp_dir, test_credentials, mock_token_response):
        """자격증명 업데이트 플로우 테스트"""
        # 초기 자격증명 저장
        cred_manager = CredentialManager(storage_path=temp_dir)
        cred_manager.save_credentials(test_credentials)
        
        # OAuth 매니저로 토큰 발급
        oauth_manager = OAuth2Manager(
            app_key=test_credentials.app_key,
            app_secret=test_credentials.app_secret,
            base_url="https://api.test.com"
        )
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token1 = await oauth_manager.get_access_token()
            assert token1 is not None
        
        # 자격증명 업데이트
        new_credentials = Credentials(
            app_key="new_app_key",
            app_secret="new_app_secret",
            account_no="99999999",
            account_type="futures"
        )
        cred_manager.save_credentials(new_credentials)
        
        # 새 OAuth 매니저로 토큰 발급
        new_oauth_manager = OAuth2Manager(
            app_key=new_credentials.app_key,
            app_secret=new_credentials.app_secret,
            base_url="https://api.test.com"
        )
        
        # 새로운 토큰 응답
        new_token_response = {
            "access_token": "new_access_token_67890",
            "token_type": "Bearer",
            "expires_in": 7200
        }
        
        new_mock_response = AsyncMock()
        new_mock_response.json = AsyncMock(return_value=new_token_response)
        new_mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = new_mock_response
            
            token2 = await new_oauth_manager.get_access_token()
            assert token2 == "new_access_token_67890"
            assert token2 != token1
    
    @pytest.mark.asyncio
    async def test_token_lifecycle_management(self, temp_dir, test_credentials):
        """토큰 생명주기 관리 통합 테스트"""
        # 자격증명 저장
        cred_manager = CredentialManager(storage_path=temp_dir)
        cred_manager.save_credentials(test_credentials)
        loaded_creds = cred_manager.load_credentials()
        
        # OAuth 매니저 생성
        oauth_manager = OAuth2Manager(
            app_key=loaded_creds.app_key,
            app_secret=loaded_creds.app_secret,
            base_url="https://api.test.com"
        )
        
        # 1. 초기 토큰 발급
        initial_token_response = {
            "access_token": "initial_token",
            "token_type": "Bearer",
            "expires_in": 300  # 5분
        }
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=initial_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token1 = await oauth_manager.get_access_token()
            assert token1 == "initial_token"
        
        # 2. 캐시된 토큰 사용
        token2 = await oauth_manager.get_access_token()
        assert token2 == token1  # 같은 토큰
        
        # 3. 토큰 만료 시뮬레이션
        oauth_manager.token_info.expires_at = datetime.now() - timedelta(minutes=1)
        
        # 4. 새 토큰 발급
        refreshed_token_response = {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 7200
        }
        
        new_mock_response = AsyncMock()
        new_mock_response.json = AsyncMock(return_value=refreshed_token_response)
        new_mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = new_mock_response
            
            token3 = await oauth_manager.get_access_token()
            assert token3 == "refreshed_token"
            assert token3 != token1
        
        # 5. 토큰 폐기
        revoke_response = AsyncMock()
        revoke_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = revoke_response
            
            result = await oauth_manager.revoke_token()
            assert result is True
            assert oauth_manager.token_info is None
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, temp_dir, test_credentials):
        """에러 복구 통합 테스트"""
        # 자격증명 저장
        cred_manager = CredentialManager(storage_path=temp_dir)
        cred_manager.save_credentials(test_credentials)
        
        # OAuth 매니저 생성
        oauth_manager = OAuth2Manager(
            app_key=test_credentials.app_key,
            app_secret=test_credentials.app_secret,
            base_url="https://api.test.com"
        )
        
        # 첫 번째 시도 실패
        fail_response = AsyncMock()
        fail_response.status = 500
        fail_response.text = AsyncMock(return_value="Server Error")
        fail_response.raise_for_status.side_effect = Exception("Server Error")
        
        # 재시도 후 성공
        success_response = AsyncMock()
        success_response.json = AsyncMock(return_value={
            "access_token": "recovered_token",
            "token_type": "Bearer",
            "expires_in": 7200
        })
        success_response.status = 200
        
        responses = [fail_response, fail_response, success_response]
        response_iter = iter(responses)
        
        async def mock_post(*args, **kwargs):
            return next(response_iter)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_context = AsyncMock()
            mock_context.__aenter__ = mock_post
            mock_session.return_value.__aenter__.return_value.post.return_value = mock_context
            
            # 재시도 로직이 작동하여 최종적으로 성공
            token = await oauth_manager.get_access_token()
            assert token == "recovered_token"