"""
API 클라이언트 팩토리
"""
import os
from typing import Union

from ..auth.credential_manager import CredentialManager, Credentials
from .kiwoom_api_client import KiwoomAPIClient
from .mock_client import MockKiwoomAPIClient


class ClientFactory:
    """API 클라이언트 팩토리"""
    
    @staticmethod
    def create_client(
        use_mock: bool = None,
        credentials: Credentials = None,
        base_url: str = None,
        **kwargs
    ) -> Union[KiwoomAPIClient, MockKiwoomAPIClient]:
        """
        API 클라이언트 생성
        
        Args:
            use_mock: Mock 클라이언트 사용 여부 (None이면 환경변수 확인)
            credentials: 인증 자격증명 (None이면 자동 로드)
            base_url: API 기본 URL (None이면 환경변수 확인)
            **kwargs: 클라이언트 추가 옵션
            
        Returns:
            API 클라이언트 인스턴스
        """
        # Mock 사용 여부 결정
        if use_mock is None:
            use_mock = os.getenv("USE_MOCK_API", "false").lower() == "true"
        
        # 자격증명 로드
        if credentials is None:
            credential_manager = CredentialManager()
            credentials = credential_manager.load_credentials()
            
            if credentials is None:
                raise ValueError("No credentials found. Please set credentials or environment variables.")
        
        # 기본 URL 설정
        if base_url is None:
            if use_mock:
                base_url = os.getenv("KIWOOM_MOCK_API_URL", "https://mockapi.kiwoom.com")
            else:
                base_url = os.getenv("KIWOOM_API_URL", "https://api.kiwoom.com")
        
        # 환경변수에서 클라이언트 옵션 로드
        client_options = {
            "rate_limit": int(os.getenv("API_RATE_LIMIT", "10")),
            "cache_ttl": int(os.getenv("CACHE_TTL", "300")),
            "max_retries": 3,
            "timeout": int(os.getenv("API_TIMEOUT", "30"))
        }
        client_options.update(kwargs)
        
        # 클라이언트 생성
        if use_mock:
            return MockKiwoomAPIClient(
                base_url=base_url,
                credentials=credentials,
                **client_options
            )
        else:
            return KiwoomAPIClient(
                base_url=base_url,
                credentials=credentials,
                **client_options
            )
    
    @staticmethod
    def create_test_client(**kwargs) -> MockKiwoomAPIClient:
        """테스트용 Mock 클라이언트 생성"""
        test_credentials = Credentials(
            app_key="test_app_key",
            app_secret="test_app_secret",
            account_no="12345678",
            account_type="stock"
        )
        
        # 기본값 설정
        defaults = {
            "base_url": "https://test.api.com",
            "credentials": test_credentials,
            "rate_limit": 100,  # 테스트시 높은 제한
            "cache_ttl": 10,    # 짧은 캐시
        }
        
        # kwargs로 덮어쓰기
        defaults.update(kwargs)
        
        return MockKiwoomAPIClient(**defaults)