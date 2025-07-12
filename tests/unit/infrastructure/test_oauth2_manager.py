"""
OAuth2 인증 관리자 테스트
"""
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientResponseError

from src.infrastructure.api.auth.oauth2_manager import OAuth2Manager, TokenInfo


class TestOAuth2Manager:
    """OAuth2Manager 테스트"""
    
    @pytest.fixture
    def oauth_config(self):
        """OAuth 설정"""
        return {
            "app_key": "test_app_key",
            "app_secret": "test_app_secret",
            "base_url": "https://api.test.com",
            "token_endpoint": "/oauth2/token"
        }
    
    @pytest.fixture
    def mock_token_response(self):
        """Mock 토큰 응답"""
        return {
            "access_token": "test_access_token_12345",
            "token_type": "Bearer",
            "expires_in": 7200,  # 2시간
            "expires_dt": (datetime.now() + timedelta(hours=2)).isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_oauth_manager_initialization(self, oauth_config):
        """OAuth 매니저 초기화 테스트"""
        manager = OAuth2Manager(
            app_key=oauth_config["app_key"],
            app_secret=oauth_config["app_secret"],
            base_url=oauth_config["base_url"]
        )
        
        assert manager.app_key == oauth_config["app_key"]
        assert manager.app_secret == oauth_config["app_secret"]
        assert manager.base_url == oauth_config["base_url"]
        assert manager.token_info is None
    
    @pytest.mark.asyncio
    async def test_get_access_token_first_time(self, oauth_config, mock_token_response):
        """최초 토큰 발급 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token = await manager.get_access_token()
            
            assert token == "test_access_token_12345"
            assert manager.token_info is not None
            assert manager.token_info.access_token == token
            assert manager.token_info.expires_at > datetime.now()
    
    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, oauth_config):
        """캐시된 토큰 반환 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # 유효한 토큰 설정
        manager.token_info = TokenInfo(
            access_token="cached_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # HTTP 호출 없이 캐시된 토큰 반환
        token = await manager.get_access_token()
        
        assert token == "cached_token"
    
    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(self, oauth_config, mock_token_response):
        """만료된 토큰 자동 갱신 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # 만료된 토큰 설정
        manager.token_info = TokenInfo(
            access_token="expired_token",
            token_type="Bearer",
            expires_at=datetime.now() - timedelta(minutes=1)  # 1분 전 만료
        )
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token = await manager.get_access_token()
            
            assert token == "test_access_token_12345"
            assert token != "expired_token"
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_buffer(self, oauth_config, mock_token_response):
        """토큰 버퍼 시간 테스트 (만료 5분 전 갱신)"""
        manager = OAuth2Manager(**oauth_config)
        
        # 4분 후 만료되는 토큰 (버퍼 시간 내)
        manager.token_info = TokenInfo(
            access_token="soon_expired_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(minutes=4)
        )
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            token = await manager.get_access_token()
            
            # 버퍼 시간 내이므로 새 토큰 발급
            assert token == "test_access_token_12345"
    
    @pytest.mark.asyncio
    async def test_concurrent_token_requests(self, oauth_config, mock_token_response):
        """동시 토큰 요청 처리 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # Mock HTTP 응답 (딜레이 추가)
        async def delayed_response():
            await asyncio.sleep(0.1)  # 100ms 딜레이
            return mock_token_response
        
        mock_response = AsyncMock()
        mock_response.json = delayed_response
        mock_response.status = 200
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.post.return_value = mock_context
            
            # 동시에 5개의 토큰 요청
            tasks = [manager.get_access_token() for _ in range(5)]
            tokens = await asyncio.gather(*tasks)
            
            # 모든 요청이 같은 토큰을 받아야 함
            assert all(token == tokens[0] for token in tokens)
            # API는 한 번만 호출되어야 함
            assert mock_session.return_value.__aenter__.return_value.post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, oauth_config):
        """토큰 폐기 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # 유효한 토큰 설정
        manager.token_info = TokenInfo(
            access_token="token_to_revoke",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP 응답
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await manager.revoke_token()
            
            assert result is True
            assert manager.token_info is None
    
    @pytest.mark.asyncio
    async def test_error_handling(self, oauth_config):
        """에러 처리 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # Mock HTTP 에러 응답
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.raise_for_status.side_effect = ClientResponseError(
            request_info=Mock(),
            history=Mock(),
            status=401
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception) as exc_info:
                await manager.get_access_token()
            
            assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_token_validation(self, oauth_config):
        """토큰 유효성 검증 테스트"""
        manager = OAuth2Manager(**oauth_config)
        
        # 토큰이 없을 때
        assert not manager.is_token_valid()
        
        # 유효한 토큰
        manager.token_info = TokenInfo(
            access_token="valid_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert manager.is_token_valid()
        
        # 만료된 토큰
        manager.token_info.expires_at = datetime.now() - timedelta(minutes=1)
        assert not manager.is_token_valid()
    
    def test_token_info_model(self):
        """TokenInfo 모델 테스트"""
        expires_at = datetime.now() + timedelta(hours=2)
        
        token_info = TokenInfo(
            access_token="test_token",
            token_type="Bearer",
            expires_at=expires_at
        )
        
        assert token_info.access_token == "test_token"
        assert token_info.token_type == "Bearer"
        assert token_info.expires_at == expires_at
        
        # 문자열 표현
        assert "test_token" in str(token_info)