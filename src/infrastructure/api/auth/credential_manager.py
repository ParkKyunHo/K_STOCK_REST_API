"""
자격증명 관리자
"""
import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """자격증명 관련 에러"""
    pass


@dataclass
class Credentials:
    """API 자격증명"""
    app_key: str
    app_secret: str
    account_no: str
    account_type: str = "stock"
    
    def __post_init__(self):
        """유효성 검증"""
        if not self.app_key:
            raise CredentialError("app_key is required")
        if not self.app_secret:
            raise CredentialError("app_secret is required")
        if not self.account_no:
            raise CredentialError("account_no is required")
    
    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Credentials":
        """딕셔너리에서 생성"""
        return cls(**data)
    
    def __str__(self) -> str:
        """보안을 위해 민감정보 마스킹"""
        return (
            f"Credentials("
            f"app_key=***{self.app_key[-4:] if len(self.app_key) > 4 else '***'}, "
            f"account_no={self.account_no}, "
            f"account_type={self.account_type})"
        )


class CredentialManager:
    """자격증명 관리자"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        초기화
        
        Args:
            storage_path: 자격증명 저장 경로
        """
        self.storage_path = Path(storage_path or os.path.expanduser("~/.kiwoom_backtest"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._credential_file = self.storage_path / "credentials.enc"
        self._key_file = self.storage_path / ".key"
        
        # 암호화 키 초기화
        self._encryption_key = self._get_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        
        logger.info(f"CredentialManager initialized with path: {self.storage_path}")
    
    def _get_or_create_key(self) -> bytes:
        """암호화 키 가져오기 또는 생성"""
        # 환경변수에서 키 확인
        env_key = os.environ.get("ENCRYPTION_KEY")
        if env_key:
            # 32자로 패딩/자르기
            key_str = env_key.ljust(32)[:32]
            return Fernet.generate_key()  # 실제로는 환경변수 기반 키 생성 필요
        
        # 키 파일 확인
        if self._key_file.exists():
            with open(self._key_file, 'rb') as f:
                return f.read()
        
        # 새 키 생성
        key = Fernet.generate_key()
        with open(self._key_file, 'wb') as f:
            f.write(key)
        
        # 키 파일 권한 설정 (읽기 전용)
        self._key_file.chmod(0o600)
        
        return key
    
    def save_credentials(self, credentials: Credentials) -> None:
        """
        자격증명 저장 (암호화)
        
        Args:
            credentials: 저장할 자격증명
        """
        try:
            # 유효성 검증은 Credentials.__post_init__에서 수행됨
            
            # JSON으로 직렬화
            data = json.dumps(credentials.to_dict())
            
            # 암호화
            encrypted_data = self._fernet.encrypt(data.encode())
            
            # 파일에 저장
            with open(self._credential_file, 'wb') as f:
                f.write(encrypted_data)
            
            # 파일 권한 설정
            self._credential_file.chmod(0o600)
            
            logger.info("Credentials saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise CredentialError(f"Failed to save credentials: {e}")
    
    def load_credentials(self) -> Optional[Credentials]:
        """
        자격증명 로드 (복호화)
        
        Returns:
            자격증명 또는 None
        """
        # 1. 파일에서 로드 시도
        if self._credential_file.exists():
            try:
                with open(self._credential_file, 'rb') as f:
                    encrypted_data = f.read()
                
                # 복호화
                decrypted_data = self._fernet.decrypt(encrypted_data)
                
                # JSON 파싱
                data = json.loads(decrypted_data.decode())
                
                # Credentials 객체 생성
                return Credentials.from_dict(data)
                
            except Exception as e:
                logger.warning(f"Failed to load credentials from file: {e}")
        
        # 2. 환경변수에서 로드 시도
        env_creds = self._load_from_env()
        if env_creds:
            logger.info("Loaded credentials from environment variables")
            return env_creds
        
        # 3. 자격증명을 찾을 수 없음
        logger.warning("No credentials found")
        return None
    
    def _load_from_env(self) -> Optional[Credentials]:
        """환경변수에서 자격증명 로드"""
        app_key = os.environ.get("KIWOOM_APP_KEY")
        app_secret = os.environ.get("KIWOOM_APP_SECRET")
        account_no = os.environ.get("KIWOOM_ACCOUNT_NO")
        account_type = os.environ.get("KIWOOM_ACCOUNT_TYPE", "stock")
        
        if all([app_key, app_secret, account_no]):
            try:
                return Credentials(
                    app_key=app_key,
                    app_secret=app_secret,
                    account_no=account_no,
                    account_type=account_type
                )
            except CredentialError:
                pass
        
        return None
    
    def delete_credentials(self) -> None:
        """저장된 자격증명 삭제"""
        if self._credential_file.exists():
            self._credential_file.unlink()
            logger.info("Credentials deleted")
    
    def update_credentials(self, **kwargs) -> None:
        """
        자격증명 업데이트
        
        Args:
            **kwargs: 업데이트할 필드
        """
        # 현재 자격증명 로드
        current = self.load_credentials()
        if not current:
            raise CredentialError("No credentials to update")
        
        # 업데이트
        updated_data = current.to_dict()
        updated_data.update(kwargs)
        
        # 새 자격증명 생성 및 저장
        new_creds = Credentials.from_dict(updated_data)
        self.save_credentials(new_creds)
    
    def has_credentials(self) -> bool:
        """자격증명 존재 여부 확인"""
        return self._credential_file.exists() or self._load_from_env() is not None