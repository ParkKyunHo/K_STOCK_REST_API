"""
통합 인증 서비스
"""
import logging
from typing import Dict, Optional

from .credential_manager import CredentialManager, Credentials
from .oauth2_manager import OAuth2Manager

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """인증 관련 에러"""
    pass


class AuthenticationService:
    """통합 인증 서비스"""
    
    def __init__(
        self,
        base_url: str,
        storage_path: Optional[str] = None,
        token_endpoint: str = "/oauth2/token",
        revoke_endpoint: str = "/oauth2/revoke"
    ):
        """
        초기화
        
        Args:
            base_url: API 기본 URL
            storage_path: 자격증명 저장 경로
            token_endpoint: 토큰 발급 엔드포인트
            revoke_endpoint: 토큰 폐기 엔드포인트
        """
        self.base_url = base_url
        self.token_endpoint = token_endpoint
        self.revoke_endpoint = revoke_endpoint
        
        # 자격증명 관리자 초기화
        self.credential_manager = CredentialManager(storage_path)
        
        # OAuth 매니저는 자격증명 설정 시 생성
        self._oauth_manager: Optional[OAuth2Manager] = None
        
        logger.info(f"AuthenticationService initialized for {base_url}")
    
    async def initialize(self) -> None:
        """
        저장된 자격증명으로 자동 초기화
        """
        credentials = self.credential_manager.load_credentials()
        if credentials:
            await self._create_oauth_manager(credentials)
            logger.info("Automatically initialized with stored credentials")
    
    async def set_credentials(self, credentials: Credentials) -> None:
        """
        자격증명 설정 및 저장
        
        Args:
            credentials: API 자격증명
        """
        # 자격증명 저장
        self.credential_manager.save_credentials(credentials)
        
        # OAuth 매니저 생성
        await self._create_oauth_manager(credentials)
        
        logger.info("Credentials set and OAuth manager created")
    
    async def _create_oauth_manager(self, credentials: Credentials) -> None:
        """OAuth 매니저 생성"""
        self._oauth_manager = OAuth2Manager(
            app_key=credentials.app_key,
            app_secret=credentials.app_secret,
            base_url=self.base_url,
            token_endpoint=self.token_endpoint,
            revoke_endpoint=self.revoke_endpoint
        )
    
    def is_authenticated(self) -> bool:
        """
        인증 상태 확인
        
        Returns:
            인증 여부
        """
        return self._oauth_manager is not None
    
    async def get_access_token(self) -> str:
        """
        액세스 토큰 획득
        
        Returns:
            액세스 토큰
            
        Raises:
            AuthenticationError: 인증되지 않음
        """
        if not self._oauth_manager:
            raise AuthenticationError("Not authenticated. Please set credentials first.")
        
        try:
            return await self._oauth_manager.get_access_token()
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise AuthenticationError(f"Failed to get access token: {e}")
    
    async def get_authenticated_headers(self) -> Dict[str, str]:
        """
        인증 헤더 생성
        
        Returns:
            Authorization 헤더를 포함한 딕셔너리
        """
        if not self._oauth_manager:
            raise AuthenticationError("Not authenticated. Please set credentials first.")
        
        return await self._oauth_manager.get_headers()
    
    async def clear_authentication(self) -> None:
        """
        인증 정보 삭제
        """
        # 토큰 폐기
        if self._oauth_manager:
            try:
                await self._oauth_manager.revoke_token()
            except Exception as e:
                logger.warning(f"Failed to revoke token: {e}")
        
        # OAuth 매니저 제거
        self._oauth_manager = None
        
        # 저장된 자격증명 삭제
        self.credential_manager.delete_credentials()
        
        logger.info("Authentication cleared")
    
    async def get_account_info(self) -> Dict[str, str]:
        """
        계좌 정보 조회 (보안 정보 제외)
        
        Returns:
            계좌 정보 딕셔너리
        """
        credentials = self.credential_manager.load_credentials()
        if not credentials:
            raise AuthenticationError("No credentials found")
        
        return {
            "account_no": credentials.account_no,
            "account_type": credentials.account_type
        }
    
    async def health_check(self) -> bool:
        """
        인증 시스템 헬스 체크
        
        Returns:
            정상 여부
        """
        try:
            if not self.is_authenticated():
                return False
            
            # 토큰 발급 시도
            await self.get_access_token()
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def refresh_token(self) -> str:
        """
        토큰 강제 갱신
        
        Returns:
            새로운 액세스 토큰
        """
        if not self._oauth_manager:
            raise AuthenticationError("Not authenticated")
        
        # 현재 토큰 무효화
        self._oauth_manager.token_info = None
        
        # 새 토큰 발급
        return await self.get_access_token()
    
    async def update_credentials(self, **kwargs) -> None:
        """
        자격증명 부분 업데이트
        
        Args:
            **kwargs: 업데이트할 필드
        """
        # 현재 자격증명 업데이트
        self.credential_manager.update_credentials(**kwargs)
        
        # OAuth 매니저 재생성
        updated_credentials = self.credential_manager.load_credentials()
        if updated_credentials:
            await self._create_oauth_manager(updated_credentials)
            logger.info("Credentials updated and OAuth manager recreated")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self._oauth_manager:
            await self._oauth_manager.close()
    
    def __str__(self) -> str:
        """문자열 표현"""
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"AuthenticationService(base_url={self.base_url}, status={status})"