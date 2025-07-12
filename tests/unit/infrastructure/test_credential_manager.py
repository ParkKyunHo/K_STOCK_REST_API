"""
자격증명 관리자 테스트
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.api.auth.credential_manager import (
    CredentialManager,
    Credentials,
    CredentialError
)


class TestCredentialManager:
    """CredentialManager 테스트"""
    
    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def credentials(self):
        """테스트용 자격증명"""
        return Credentials(
            app_key="test_app_key_12345",
            app_secret="test_app_secret_67890",
            account_no="12345678",
            account_type="stock"
        )
    
    @pytest.fixture
    def mock_env(self):
        """Mock 환경변수"""
        env_vars = {
            "KIWOOM_APP_KEY": "env_app_key",
            "KIWOOM_APP_SECRET": "env_app_secret",
            "KIWOOM_ACCOUNT_NO": "87654321"
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars
    
    def test_credential_manager_initialization(self, temp_dir):
        """자격증명 관리자 초기화 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        assert manager.storage_path == Path(temp_dir)
        assert manager._encryption_key is not None
    
    def test_save_credentials_encrypted(self, temp_dir, credentials):
        """자격증명 암호화 저장 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 자격증명 저장
        manager.save_credentials(credentials)
        
        # 파일이 생성되었는지 확인
        cred_file = Path(temp_dir) / "credentials.enc"
        assert cred_file.exists()
        
        # 파일 내용이 암호화되었는지 확인
        with open(cred_file, 'rb') as f:
            encrypted_data = f.read()
        
        # 원본 데이터가 포함되지 않았는지 확인
        assert b"test_app_key_12345" not in encrypted_data
        assert b"test_app_secret_67890" not in encrypted_data
    
    def test_load_credentials_decryption(self, temp_dir, credentials):
        """자격증명 복호화 로드 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 저장
        manager.save_credentials(credentials)
        
        # 로드
        loaded_creds = manager.load_credentials()
        
        assert loaded_creds is not None
        assert loaded_creds.app_key == credentials.app_key
        assert loaded_creds.app_secret == credentials.app_secret
        assert loaded_creds.account_no == credentials.account_no
        assert loaded_creds.account_type == credentials.account_type
    
    def test_load_credentials_from_env(self, temp_dir, mock_env):
        """환경변수에서 자격증명 로드 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 파일이 없을 때 환경변수에서 로드
        creds = manager.load_credentials()
        
        assert creds is not None
        assert creds.app_key == mock_env["KIWOOM_APP_KEY"]
        assert creds.app_secret == mock_env["KIWOOM_APP_SECRET"]
        assert creds.account_no == mock_env["KIWOOM_ACCOUNT_NO"]
    
    def test_load_credentials_file_priority(self, temp_dir, credentials, mock_env):
        """파일 우선순위 테스트 (파일 > 환경변수)"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 파일 저장
        manager.save_credentials(credentials)
        
        # 환경변수가 있어도 파일에서 로드
        loaded_creds = manager.load_credentials()
        
        assert loaded_creds.app_key == credentials.app_key  # 파일 값
        assert loaded_creds.app_key != mock_env["KIWOOM_APP_KEY"]  # 환경변수 값 아님
    
    def test_delete_credentials(self, temp_dir, credentials):
        """자격증명 삭제 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 저장
        manager.save_credentials(credentials)
        cred_file = Path(temp_dir) / "credentials.enc"
        assert cred_file.exists()
        
        # 삭제
        manager.delete_credentials()
        assert not cred_file.exists()
        
        # 로드 시도
        loaded = manager.load_credentials()
        assert loaded is None  # 환경변수도 없으면 None
    
    def test_update_credentials(self, temp_dir, credentials):
        """자격증명 업데이트 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 초기 저장
        manager.save_credentials(credentials)
        
        # 업데이트
        new_creds = Credentials(
            app_key="new_app_key",
            app_secret="new_app_secret",
            account_no="99999999",
            account_type="futures"
        )
        manager.save_credentials(new_creds)
        
        # 로드하여 확인
        loaded = manager.load_credentials()
        assert loaded.app_key == "new_app_key"
        assert loaded.account_no == "99999999"
        assert loaded.account_type == "futures"
    
    def test_credentials_validation(self, temp_dir):
        """자격증명 유효성 검증 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 필수 필드 누락
        invalid_creds = Credentials(
            app_key="",  # 빈 값
            app_secret="secret",
            account_no="12345678"
        )
        
        with pytest.raises(CredentialError) as exc_info:
            manager.save_credentials(invalid_creds)
        
        assert "app_key" in str(exc_info.value)
    
    def test_encryption_key_persistence(self, temp_dir):
        """암호화 키 지속성 테스트"""
        # 첫 번째 매니저
        manager1 = CredentialManager(storage_path=temp_dir)
        creds = Credentials(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678"
        )
        manager1.save_credentials(creds)
        
        # 두 번째 매니저 (같은 디렉토리)
        manager2 = CredentialManager(storage_path=temp_dir)
        loaded = manager2.load_credentials()
        
        # 다른 인스턴스에서도 복호화 가능해야 함
        assert loaded is not None
        assert loaded.app_key == creds.app_key
    
    def test_custom_encryption_key(self, temp_dir):
        """사용자 정의 암호화 키 테스트"""
        custom_key = "my_custom_encryption_key_32_char"
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": custom_key}):
            manager = CredentialManager(storage_path=temp_dir)
            
            creds = Credentials(
                app_key="test",
                app_secret="secret",
                account_no="12345"
            )
            manager.save_credentials(creds)
            
            # 로드 확인
            loaded = manager.load_credentials()
            assert loaded.app_key == "test"
    
    def test_credentials_model(self):
        """Credentials 모델 테스트"""
        creds = Credentials(
            app_key="key",
            app_secret="secret",
            account_no="12345678",
            account_type="stock"
        )
        
        # to_dict
        creds_dict = creds.to_dict()
        assert creds_dict["app_key"] == "key"
        assert creds_dict["app_secret"] == "secret"
        assert creds_dict["account_no"] == "12345678"
        assert creds_dict["account_type"] == "stock"
        
        # from_dict
        new_creds = Credentials.from_dict(creds_dict)
        assert new_creds.app_key == creds.app_key
        assert new_creds.app_secret == creds.app_secret
        
        # 문자열 표현 (보안)
        str_repr = str(creds)
        assert "***" in str_repr
        assert "secret" not in str_repr
    
    def test_error_handling(self, temp_dir):
        """에러 처리 테스트"""
        manager = CredentialManager(storage_path=temp_dir)
        
        # 잘못된 암호화 파일
        cred_file = Path(temp_dir) / "credentials.enc"
        with open(cred_file, 'wb') as f:
            f.write(b"invalid encrypted data")
        
        # 복호화 실패
        loaded = manager.load_credentials()
        assert loaded is None  # 에러 시 None 반환 (또는 환경변수 시도)