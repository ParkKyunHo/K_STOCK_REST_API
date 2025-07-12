"""
pytest 전역 fixture 및 설정
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio
from aiohttp import ClientSession

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 설정
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """테스트용 설정"""
    return {
        "api": {
            "base_url": "https://mock.api.kiwoom.com",
            "timeout": 30,
            "rate_limit": {"calls_per_second": 10}
        },
        "cache": {
            "backend": "memory",
            "ttl": {"default": 60}
        },
        "logging": {
            "level": "DEBUG"
        }
    }


@pytest.fixture
def mock_api_response():
    """API 응답 mock"""
    return {
        "status": "success",
        "data": {
            "symbol": "005930",
            "price": 70000,
            "volume": 1000000
        }
    }


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """HTTP 세션 fixture"""
    async with ClientSession() as session:
        yield session


@pytest.fixture
def mock_oauth_manager():
    """OAuth 매니저 mock"""
    manager = Mock()
    manager.get_access_token = AsyncMock(return_value="mock_token_12345")
    manager.token = "mock_token_12345"
    manager.is_token_valid = Mock(return_value=True)
    return manager


@pytest.fixture
def sample_market_data():
    """샘플 시장 데이터"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    dates = pd.date_range(
        end=datetime.now().date(),
        periods=100,
        freq='D'
    )
    
    data = pd.DataFrame({
        'open': [70000 + i * 100 for i in range(100)],
        'high': [70500 + i * 100 for i in range(100)],
        'low': [69500 + i * 100 for i in range(100)],
        'close': [70200 + i * 100 for i in range(100)],
        'volume': [1000000 + i * 10000 for i in range(100)]
    }, index=dates)
    
    return data


@pytest.fixture
def sample_portfolio():
    """샘플 포트폴리오"""
    return {
        "cash": 5000000,
        "positions": {
            "005930": {"quantity": 100, "avg_price": 70000},
            "000660": {"quantity": 50, "avg_price": 150000}
        }
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """임시 데이터 디렉토리"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    
    # 하위 디렉토리 생성
    (data_dir / "raw").mkdir()
    (data_dir / "processed").mkdir()
    (data_dir / "cache").mkdir()
    
    return data_dir


@pytest.fixture(autouse=True)
def reset_singletons():
    """싱글톤 패턴 리셋"""
    # 테스트 간 싱글톤 인스턴스 충돌 방지
    yield
    # 필요한 경우 싱글톤 리셋 로직 추가


@pytest.fixture
def mock_strategy():
    """전략 mock"""
    from src.core.interfaces import IStrategy
    
    strategy = Mock(spec=IStrategy)
    strategy.name = "TestStrategy"
    strategy.version = "1.0.0"
    strategy.parameters = {"param1": 10, "param2": 20}
    strategy.initialize = AsyncMock()
    strategy.on_data = AsyncMock(return_value=[])
    strategy.on_order_filled = AsyncMock()
    strategy.on_day_end = AsyncMock()
    
    return strategy


# 마커별 설정
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "unit: 단위 테스트"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-End 테스트"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트"
    )


# 테스트 실행 전후 처리
@pytest.fixture(autouse=True)
def test_environment():
    """테스트 환경 설정/정리"""
    # Setup
    original_env = os.environ.copy()
    
    yield
    
    # Teardown
    os.environ.clear()
    os.environ.update(original_env)