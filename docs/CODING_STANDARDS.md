# 코딩 표준 및 규칙

## 1. 개요

이 문서는 키움증권 REST API 백테스팅 시스템 개발 시 준수해야 할 코딩 표준을 정의합니다. 일관된 코드 스타일은 가독성을 높이고 유지보수를 용이하게 합니다.

## 2. Python 코딩 스타일

### 2.1 기본 규칙

- **Python 버전**: 3.9 이상
- **스타일 가이드**: PEP 8 준수
- **라인 길이**: 최대 88자 (Black 기본값)
- **인코딩**: UTF-8

### 2.2 포맷팅 도구

```bash
# 코드 포맷팅
black .

# import 정렬
isort .

# 타입 체크
mypy src/

# 린팅
pylint src/
flake8 src/
```

### 2.3 테스트 우선 개발 (TDD)

**모든 코드는 테스트 우선 개발 방식을 따라야 합니다.**

```python
# 1. 테스트 먼저 작성 (실패하는 테스트)
def test_calculate_returns():
    """수익률 계산 테스트"""
    prices = pd.Series([100, 110, 121])
    expected = pd.Series([0.1, 0.1])
    
    result = calculate_returns(prices)
    
    pd.testing.assert_series_equal(result, expected)

# 2. 최소한의 코드로 테스트 통과
def calculate_returns(prices: pd.Series) -> pd.Series:
    """일일 수익률 계산"""
    return prices.pct_change().dropna()

# 3. 리팩토링 및 개선
def calculate_returns(
    prices: pd.Series,
    method: str = "simple"
) -> pd.Series:
    """
    일일 수익률 계산
    
    Args:
        prices: 가격 시계열
        method: 계산 방법 ('simple', 'log')
        
    Returns:
        수익률 시계열
    """
    if method == "simple":
        return prices.pct_change().dropna()
    elif method == "log":
        return np.log(prices / prices.shift(1)).dropna()
    else:
        raise ValueError(f"Unknown method: {method}")
```

### 2.4 작업 프로세스

1. **테스트 작성** → 2. **구현** → 3. **테스트 실행** → 4. **문서 업데이트**

자세한 내용은 [WORKFLOW.md](WORKFLOW.md) 참조

## 3. 명명 규칙

### 3.1 기본 명명 규칙

```python
# 모듈명: 소문자, 언더스코어 구분
market_data_provider.py

# 클래스명: PascalCase
class MarketDataProvider:
    pass

# 함수/메서드명: snake_case
def calculate_sharpe_ratio(returns: pd.Series) -> float:
    pass

# 변수명: snake_case
total_return = 0.0
portfolio_value = 1000000

# 상수: 대문자, 언더스코어 구분
MAX_RETRY_COUNT = 3
DEFAULT_COMMISSION_RATE = 0.00015

# 프라이빗 속성/메서드: 언더스코어 접두사
class Portfolio:
    def __init__(self):
        self._positions = {}
    
    def _calculate_exposure(self):
        pass
```

### 3.2 특수 명명 규칙

```python
# 인터페이스: I 접두사
class IStrategy(ABC):
    pass

# 추상 클래스: Abstract 접두사
class AbstractDataProvider(ABC):
    pass

# 예외 클래스: Error/Exception 접미사
class APIConnectionError(Exception):
    pass

# 타입 별칭: PascalCase
OrderDict = Dict[str, Order]
PriceHistory = pd.DataFrame
```

## 4. 타입 힌팅

### 4.1 기본 타입 힌팅

```python
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from datetime import datetime
import pandas as pd
import numpy as np

# 함수 시그니처
def fetch_market_data(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1d"
) -> pd.DataFrame:
    """시장 데이터 조회"""
    pass

# Optional 사용
def get_position(symbol: str) -> Optional[Position]:
    """포지션 조회 (없으면 None)"""
    pass

# Union 사용
def parse_price(value: Union[str, float, int]) -> float:
    """가격 파싱"""
    pass

# 복잡한 타입
StrategyResult = Dict[str, Union[float, pd.Series, Dict[str, Any]]]

def backtest_strategy(
    strategy: IStrategy,
    data: pd.DataFrame
) -> StrategyResult:
    pass
```

### 4.2 제네릭 타입

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Cache(Generic[T]):
    """제네릭 캐시 구현"""
    
    def __init__(self):
        self._cache: Dict[str, T] = {}
    
    def get(self, key: str) -> Optional[T]:
        return self._cache.get(key)
    
    def set(self, key: str, value: T) -> None:
        self._cache[key] = value
```

## 5. 비동기 프로그래밍

### 5.1 비동기 함수

```python
import asyncio
from typing import AsyncIterator, Awaitable

# 비동기 함수 정의
async def fetch_realtime_data(symbol: str) -> Dict[str, Any]:
    """실시간 데이터 조회"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/api/quote/{symbol}") as response:
            return await response.json()

# 비동기 컨텍스트 매니저
class AsyncDatabaseConnection:
    async def __aenter__(self):
        self.conn = await asyncpg.connect(DATABASE_URL)
        return self.conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()

# 비동기 이터레이터
async def stream_market_data(symbols: List[str]) -> AsyncIterator[Dict]:
    """시장 데이터 스트리밍"""
    async for data in websocket_stream(symbols):
        yield process_market_data(data)
```

### 5.2 동시성 처리

```python
# 동시 실행
async def fetch_multiple_symbols(symbols: List[str]) -> List[pd.DataFrame]:
    """여러 종목 동시 조회"""
    tasks = [fetch_market_data(symbol) for symbol in symbols]
    return await asyncio.gather(*tasks)

# 세마포어를 이용한 동시성 제한
class RateLimitedClient:
    def __init__(self, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def request(self, url: str) -> Dict:
        async with self._semaphore:
            return await self._make_request(url)
```

## 6. 에러 처리

### 6.1 예외 정의

```python
# 커스텀 예외 계층 구조
class BacktestError(Exception):
    """백테스트 시스템 기본 예외"""
    pass

class DataError(BacktestError):
    """데이터 관련 예외"""
    pass

class StrategyError(BacktestError):
    """전략 실행 예외"""
    pass

class APIError(BacktestError):
    """API 호출 예외"""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
```

### 6.2 예외 처리 패턴

```python
# 구체적인 예외 처리
async def safe_api_call(api_id: str, params: Dict) -> Dict:
    """안전한 API 호출"""
    try:
        response = await api_client.request(api_id, params)
        return response
    except APIError as e:
        logger.error(f"API error {e.status_code}: {e}")
        raise
    except asyncio.TimeoutError:
        logger.error(f"API timeout for {api_id}")
        raise APIError("Request timeout", status_code=408)
    except Exception as e:
        logger.exception(f"Unexpected error in API call {api_id}")
        raise SystemError(f"System error: {e}")

# 컨텍스트 매니저를 이용한 에러 처리
from contextlib import contextmanager

@contextmanager
def error_handler(operation: str):
    """에러 처리 컨텍스트 매니저"""
    try:
        logger.info(f"Starting {operation}")
        yield
    except Exception as e:
        logger.exception(f"Error in {operation}: {e}")
        raise
    finally:
        logger.info(f"Completed {operation}")
```

## 7. 로깅

### 7.1 로깅 규칙

```python
import logging
from typing import Any

# 로거 생성
logger = logging.getLogger(__name__)

class StrategyEngine:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def execute_strategy(self, strategy: IStrategy) -> None:
        """전략 실행"""
        self.logger.info(
            "Executing strategy",
            extra={
                "strategy_name": strategy.name,
                "parameters": strategy.parameters
            }
        )
        
        try:
            result = strategy.run()
            self.logger.info(
                "Strategy execution completed",
                extra={"result": result}
            )
        except Exception as e:
            self.logger.exception(
                "Strategy execution failed",
                extra={"strategy_name": strategy.name}
            )
            raise
```

### 7.2 구조화된 로깅

```python
# 구조화된 로그 포맷
import structlog

logger = structlog.get_logger()

def process_order(order: Order) -> None:
    """주문 처리"""
    log = logger.bind(
        order_id=order.id,
        symbol=order.symbol,
        quantity=order.quantity
    )
    
    log.info("Processing order")
    
    try:
        # 주문 처리 로직
        execute_order(order)
        log.info("Order executed successfully")
    except Exception as e:
        log.exception("Order execution failed")
        raise
```

## 8. 문서화

### 8.1 Docstring 규칙

```python
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods: int = 252
) -> float:
    """
    샤프 비율 계산
    
    샤프 비율은 위험 조정 수익률을 측정하는 지표입니다.
    
    Args:
        returns: 일별 수익률 시계열
        risk_free_rate: 무위험 수익률 (연율)
        periods: 연간 거래일 수
        
    Returns:
        샤프 비율
        
    Raises:
        ValueError: returns가 비어있거나 표준편차가 0인 경우
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.03, 0.01, -0.01])
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
    """
    if returns.empty:
        raise ValueError("Returns series is empty")
    
    excess_returns = returns - risk_free_rate / periods
    
    if returns.std() == 0:
        raise ValueError("Returns have zero standard deviation")
    
    return np.sqrt(periods) * excess_returns.mean() / returns.std()
```

### 8.2 클래스 문서화

```python
class Portfolio:
    """
    포트폴리오 관리 클래스
    
    포트폴리오의 포지션, 거래 내역, 성과를 추적합니다.
    
    Attributes:
        capital: 초기 자본금
        positions: 현재 포지션 딕셔너리
        transactions: 거래 내역 리스트
        
    Example:
        >>> portfolio = Portfolio(initial_capital=1000000)
        >>> portfolio.add_position("005930", 100, 70000)
        >>> print(portfolio.total_value)
    """
    
    def __init__(self, initial_capital: float):
        """
        포트폴리오 초기화
        
        Args:
            initial_capital: 초기 자본금
        """
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
```

## 9. 테스트 코드

### 9.0 테스트 우선 개발 원칙

**중요**: 모든 기능은 테스트를 먼저 작성한 후 구현해야 합니다.

```python
# ❌ 잘못된 방법: 구현 먼저
def calculate_profit(buy_price, sell_price, quantity):
    return (sell_price - buy_price) * quantity

# 나중에 테스트 작성...

# ✅ 올바른 방법: 테스트 먼저
def test_calculate_profit():
    """수익 계산 테스트"""
    # Given
    buy_price = 100
    sell_price = 110
    quantity = 10
    
    # When
    profit = calculate_profit(buy_price, sell_price, quantity)
    
    # Then
    assert profit == 100

# 그 다음 구현
def calculate_profit(buy_price, sell_price, quantity):
    """매매 수익 계산"""
    return (sell_price - buy_price) * quantity
```

### 테스트 작성 순서
1. **실패하는 테스트 작성** (Red)
2. **테스트를 통과하는 최소 코드 작성** (Green)
3. **코드 리팩토링** (Refactor)
4. **테스트 재실행 및 확인**

### 9.1 테스트 명명 규칙

```python
import pytest
from unittest.mock import Mock, patch

class TestPortfolio:
    """포트폴리오 테스트"""
    
    def test_초기화_시_자본금_설정(self):
        """초기화 시 자본금이 올바르게 설정되는지 테스트"""
        portfolio = Portfolio(initial_capital=1000000)
        assert portfolio.capital == 1000000
    
    def test_포지션_추가_시_자본금_감소(self):
        """포지션 추가 시 자본금이 감소하는지 테스트"""
        portfolio = Portfolio(initial_capital=1000000)
        portfolio.add_position("005930", 100, 70000)
        
        expected_capital = 1000000 - (100 * 70000)
        assert portfolio.capital == expected_capital
    
    @pytest.mark.parametrize("symbol,quantity,price", [
        ("005930", 100, 70000),
        ("000660", 50, 150000),
        ("035720", 200, 35000),
    ])
    def test_다양한_포지션_추가(self, symbol, quantity, price):
        """다양한 포지션 추가 테스트"""
        portfolio = Portfolio(initial_capital=10000000)
        portfolio.add_position(symbol, quantity, price)
        
        assert symbol in portfolio.positions
        assert portfolio.positions[symbol].quantity == quantity
```

### 9.2 비동기 테스트

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_비동기_데이터_조회():
    """비동기 데이터 조회 테스트"""
    client = MarketDataClient()
    
    data = await client.fetch_market_data("005930")
    
    assert isinstance(data, pd.DataFrame)
    assert not data.empty
    assert all(col in data.columns for col in ['open', 'high', 'low', 'close'])
```

## 10. 성능 고려사항

### 10.1 효율적인 코드 작성

```python
# Bad: 리스트 컴프리헨션 대신 반복문
result = []
for i in range(1000):
    if i % 2 == 0:
        result.append(i * 2)

# Good: 리스트 컴프리헨션 사용
result = [i * 2 for i in range(1000) if i % 2 == 0]

# Bad: 반복적인 속성 접근
for i in range(len(data)):
    process(data.values[i])

# Good: 한 번만 접근
values = data.values
for value in values:
    process(value)

# Bad: 문자열 연결
result = ""
for item in items:
    result += str(item) + ","

# Good: join 사용
result = ",".join(str(item) for item in items)
```

### 10.2 NumPy/Pandas 최적화

```python
# Bad: 반복문으로 계산
returns = []
for i in range(1, len(prices)):
    returns.append((prices[i] - prices[i-1]) / prices[i-1])

# Good: 벡터화 연산
returns = prices.pct_change().dropna()

# Bad: apply 사용
df['new_col'] = df.apply(lambda row: row['a'] + row['b'], axis=1)

# Good: 벡터화 연산
df['new_col'] = df['a'] + df['b']
```

## 11. PyQt5/Qt 코딩 표준

### 11.1 objectName 설정 (필수)

모든 QDockWidget, QToolBar, 그리고 상태 저장이 필요한 위젯에는 반드시 objectName을 설정해야 합니다.

```python
# ❌ 잘못된 예: objectName 미설정
self.strategy_dock = QDockWidget("전략 목록", self)
self.main_toolbar = self.addToolBar("메인 툴바")

# ✅ 올바른 예: objectName 설정
self.strategy_dock = QDockWidget("전략 목록", self)
self.strategy_dock.setObjectName("strategyDock")  # 필수!

self.main_toolbar = self.addToolBar("메인 툴바")
self.main_toolbar.setObjectName("mainToolbar")  # 필수!

# 커스텀 위젯도 동일
self.custom_widget = CustomWidget()
self.custom_widget.setObjectName("customWidget")
```

### 11.2 objectName 명명 규칙

- **camelCase** 사용 (Qt 표준)
- 위젯 타입을 접미사로 포함
- 명확하고 설명적인 이름 사용

```python
# 도킹 위젯
self.strategy_dock.setObjectName("strategyDock")
self.log_dock.setObjectName("logDock")
self.property_dock.setObjectName("propertyDock")

# 툴바
self.file_toolbar.setObjectName("fileToolbar")
self.edit_toolbar.setObjectName("editToolbar")

# 일반 위젯
self.search_widget.setObjectName("searchWidget")
self.result_table.setObjectName("resultTable")
```

### 11.3 한글 인코딩 처리

```python
# 파일 상단에 인코딩 명시
# -*- coding: utf-8 -*-

# 폰트 설정 시 시스템별 대응
from PyQt5.QtGui import QFont

font = QFont()
if sys.platform == "win32":
    font.setFamily("맑은 고딕")
elif sys.platform == "linux":
    font.setFamily("Noto Sans CJK KR")
elif sys.platform == "darwin":
    font.setFamily("Apple SD Gothic Neo")
font.setPointSize(10)
app.setFont(font)
```

### 11.4 시그널/슬롯 명명 규칙

```python
# 시그널 정의
class CustomWidget(QWidget):
    # 동사_과거분사 형태
    data_loaded = pyqtSignal(dict)
    item_selected = pyqtSignal(str)
    process_completed = pyqtSignal()
    
    # 슬롯 메서드는 on_ 접두사
    def on_button_clicked(self):
        pass
        
    def on_data_received(self, data):
        pass
```

### 11.5 레이아웃 관리

```python
# 레이아웃 생성 시 부모 지정 권장
layout = QVBoxLayout(self)  # 부모 지정

# 또는 명시적으로 설정
layout = QVBoxLayout()
self.setLayout(layout)

# 마진과 스페이싱 설정
layout.setContentsMargins(5, 5, 5, 5)
layout.setSpacing(10)
```

## 12. 보안 고려사항

### 11.1 민감 정보 처리

```python
# Bad: 하드코딩된 인증 정보
API_KEY = "abcd1234"
API_SECRET = "secret123"

# Good: 환경 변수 사용
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KIWOOM_API_KEY")
API_SECRET = os.getenv("KIWOOM_API_SECRET")

# 로깅 시 민감 정보 마스킹
def mask_sensitive_data(data: str) -> str:
    """민감 정보 마스킹"""
    if len(data) <= 4:
        return "****"
    return data[:2] + "*" * (len(data) - 4) + data[-2:]
```

## 12. Git 커밋 메시지

### 12.1 커밋 메시지 형식

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 12.2 타입 종류

- **feat**: 새로운 기능
- **fix**: 버그 수정
- **docs**: 문서 변경
- **style**: 코드 포맷팅
- **refactor**: 리팩토링
- **test**: 테스트 추가/수정
- **chore**: 빌드 프로세스 등

### 12.3 예시

```
feat(strategy): 이동평균 전략 구현

- 단순이동평균(SMA) 전략 클래스 추가
- 골든크로스/데드크로스 신호 생성
- 백테스트 통합 테스트 추가

Closes #123
```

---

**버전**: 1.0.0  
**작성일**: 2024-01-12  
**작성자**: Development Team