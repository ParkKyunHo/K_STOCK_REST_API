"""
예제 테스트 - 작업 프로세스 검증용
"""
import pytest


def test_example_pass():
    """통과하는 예제 테스트"""
    assert 1 + 1 == 2


def test_example_list():
    """리스트 테스트"""
    numbers = [1, 2, 3, 4, 5]
    assert len(numbers) == 5
    assert sum(numbers) == 15


@pytest.mark.asyncio
async def test_example_async():
    """비동기 테스트 예제"""
    import asyncio
    
    async def async_function():
        await asyncio.sleep(0.1)
        return "success"
    
    result = await async_function()
    assert result == "success"


class TestExample:
    """클래스 기반 테스트 예제"""
    
    def test_class_method(self):
        """클래스 메서드 테스트"""
        data = {"key": "value"}
        assert "key" in data
        assert data["key"] == "value"