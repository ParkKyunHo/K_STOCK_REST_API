"""
OAuth2 인증 관리자
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """토큰 정보"""
    access_token: str
    token_type: str
    expires_at: datetime
    
    def __str__(self) -> str:
        return f"TokenInfo(token=***{self.access_token[-5:]}, expires_at={self.expires_at})"


class OAuth2Manager:
    """OAuth2 인증 관리자"""
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        base_url: str,
        token_endpoint: str = "/oauth2/token",
        revoke_endpoint: str = "/oauth2/revoke"
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url.rstrip('/')
        self.token_endpoint = token_endpoint
        self.revoke_endpoint = revoke_endpoint
        
        self.token_info: Optional[TokenInfo] = None
        self._token_lock = asyncio.Lock()
        self._refresh_buffer = timedelta(minutes=5)  # 만료 5분 전 갱신
        
        logger.info(f"OAuth2Manager initialized for {base_url}")
    
    async def get_access_token(self) -> str:
        """
        액세스 토큰 획득
        
        Returns:
            액세스 토큰 문자열
        """
        # 토큰이 유효한 경우 캐시된 토큰 반환
        if self.is_token_valid():
            return self.token_info.access_token
        
        # 동시 요청 방지를 위한 락
        async with self._token_lock:
            # 락 획득 후 다시 확인 (다른 요청이 이미 갱신했을 수 있음)
            if self.is_token_valid():
                return self.token_info.access_token
            
            # 새 토큰 발급
            logger.info("Requesting new access token")
            await self._request_new_token()
            
            return self.token_info.access_token
    
    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _request_new_token(self) -> None:
        """새 토큰 요청"""
        url = f"{self.base_url}{self.token_endpoint}"
        
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        headers = {
            "content-type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token request failed: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                
                # 토큰 정보 저장
                self._save_token_info(data)
                
                logger.info("Successfully obtained new access token")
    
    def _save_token_info(self, token_data: dict) -> None:
        """토큰 정보 저장"""
        # expires_dt가 있으면 사용, 없으면 expires_in으로 계산
        if "expires_dt" in token_data:
            expires_at = datetime.fromisoformat(token_data["expires_dt"])
        else:
            expires_in = token_data.get("expires_in", 7200)  # 기본 2시간
            expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        self.token_info = TokenInfo(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at
        )
        
        logger.debug(f"Token saved: {self.token_info}")
    
    def is_token_valid(self) -> bool:
        """토큰 유효성 확인"""
        if not self.token_info:
            return False
        
        # 버퍼를 고려한 만료 시간 확인
        valid_until = self.token_info.expires_at - self._refresh_buffer
        return datetime.now() < valid_until
    
    async def revoke_token(self) -> bool:
        """
        토큰 폐기
        
        Returns:
            성공 여부
        """
        if not self.token_info:
            logger.warning("No token to revoke")
            return True
        
        url = f"{self.base_url}{self.revoke_endpoint}"
        
        payload = {
            "appkey": self.app_key,
            "secretkey": self.app_secret,
            "token": self.token_info.access_token
        }
        
        headers = {
            "content-type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        self.token_info = None
                        logger.info("Token revoked successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Token revocation failed: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.exception(f"Error revoking token: {e}")
            return False
    
    async def get_headers(self) -> dict:
        """
        인증 헤더 생성
        
        Returns:
            Authorization 헤더를 포함한 딕셔너리
        """
        token = await self.get_access_token()
        
        return {
            "Authorization": f"{self.token_info.token_type} {token}",
            "content-type": "application/json;charset=UTF-8"
        }
    
    async def close(self) -> None:
        """리소스 정리"""
        if self.token_info:
            await self.revoke_token()