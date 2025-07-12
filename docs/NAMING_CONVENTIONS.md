# 코딩 표준 및 명명 규칙

## 📋 개요
K-Stock REST API 프로젝트의 일관된 개발을 위한 명명 규칙과 코딩 표준을 정의합니다.

## 🏗️ 전략 시스템 명명 규칙

### 전략 클래스명
```python
# 패턴: [기능명]Strategy
class MovingAverageCrossover(BaseStrategy):  # ✅ 현재 구현
class RSIStrategy(BaseStrategy):             # ✅ 현재 구현
class BollingerBandsStrategy(BaseStrategy):  # ✅ 현재 구현

# 향후 추가 시 권장 패턴:
class MACDStrategy(BaseStrategy):
class StochasticStrategy(BaseStrategy):
class IchimokuStrategy(BaseStrategy):
```

### 전략 파라미터명
```python
# 이동평균 관련
short_period: int     # 단기 기간 (fast_period 대신)
long_period: int      # 장기 기간 (slow_period 대신)
ma_type: str         # "sma", "ema", "wma"

# RSI 관련  
rsi_period: int           # RSI 계산 기간
oversold_threshold: float # 과매도 임계값
overbought_threshold: float # 과매수 임계값

# 볼린저 밴드 관련
bb_period: int        # 볼린저 밴드 기간
bb_std: float        # 표준편차 배수 (num_std 대신)

# 공통
position_size: float  # 포지션 크기 비율 (0.0 ~ 1.0)
min_price: float     # 최소 가격 필터
max_price: float     # 최대 가격 필터
```

### 지표 클래스명
```python
# 현재 구현된 지표들
class MovingAverage(IIndicator):    # SMA, EMA, WMA
class RSI(IIndicator):             # Relative Strength Index
class BollingerBands(IIndicator):   # Bollinger Bands
class MACD(IIndicator):            # MACD
class Stochastic(IIndicator):      # Stochastic Oscillator
class ATR(IIndicator):             # Average True Range
class Williams_R(IIndicator):      # Williams %R
class CCI(IIndicator):             # Commodity Channel Index
```

## 📁 파일 및 모듈 구조

### 디렉토리 구조
```
src/strategy/
├── __init__.py
├── base.py                    # BaseStrategy, StrategyConfig, StrategyContext
├── indicators.py             # 모든 기술 지표
├── loader.py                 # StrategyLoader
├── runner.py                 # StrategyRunner, StrategyState
├── optimizer.py              # StrategyOptimizer
└── examples/                 # 샘플 전략들
    ├── __init__.py
    ├── moving_average_crossover.py
    ├── rsi_strategy.py
    └── bollinger_bands_strategy.py
```

### Import 경로
```python
# 전략 관련
from src.strategy.base import BaseStrategy, StrategyConfig, StrategyContext
from src.strategy.loader import StrategyLoader
from src.strategy.runner import StrategyRunner, StrategyState
from src.strategy.indicators import MovingAverage, RSI, BollingerBands

# 도메인 모델
from src.core.models.domain import Portfolio, Position, Transaction
from src.core.interfaces.strategy import Signal, SignalType, MarketData

# 샘플 전략
from src.strategy.examples.moving_average_crossover import MovingAverageCrossover
from src.strategy.examples.rsi_strategy import RSIStrategy
from src.strategy.examples.bollinger_bands_strategy import BollingerBandsStrategy
```

## 🔧 클래스 속성 및 메서드 규칙

### BaseStrategy 구조
```python
class BaseStrategy(IStrategy):
    # 필수 속성 (config에서 접근)
    self.config: StrategyConfig
    self.parameters: Dict[str, Any]  # config.parameters
    
    # 실행 컨텍스트
    self.context: StrategyContext
    self.logger: logging.Logger
    self.initialized: bool
    
    # 히스토리 관리
    self.data_history: List[MarketData]
    self.signals_history: List[Signal]
    
    # 성과 추적
    self.total_signals: int
    self.executed_trades: int
    
    # 필수 구현 메서드
    async def generate_signals(self, data: MarketData) -> List[Signal]:
        pass
    
    # 선택적 오버라이드 메서드
    def validate_custom_parameters(self) -> bool:
        return True
```

### Portfolio 인터페이스
```python
class Portfolio:
    # 중요: get_total_value()가 아닌 total_value 프로퍼티 사용
    @property
    def total_value(self) -> float:
        pass
    
    # 메서드로 구현된 것
    def get_total_value(self) -> float:
        return self.total_value
    
    # 속성
    cash: float
    positions: Dict[str, Position]
    transactions: List[Transaction]
```

### Signal 구조
```python
@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType  # BUY, SELL, HOLD
    strength: float         # -1.0 ~ 1.0 범위 (필수 검증)
    price: Optional[float]
    reason: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## 🧪 테스트 명명 규칙

### 테스트 파일명
```
tests/unit/strategy/
├── test_base.py              # BaseStrategy 관련 테스트
├── test_indicators.py        # 지표 라이브러리 테스트  
├── test_sample_strategies.py # 샘플 전략 테스트
└── test_loader_runner.py     # 로더/실행기 테스트
```

### 테스트 클래스 및 메서드명
```python
# 테스트 클래스명: Test + 대상클래스명
class TestMovingAverageCrossover:
class TestRSIStrategy:
class TestBollingerBandsStrategy:

# 테스트 메서드명: test_ + 기능설명
def test_strategy_parameters(self):
def test_parameter_validation(self):
def test_crossover_signal_generation(self):
def test_oversold_buy_signal(self):
```

## 📊 Mock 및 Fixture 규칙

### Portfolio Mock 설정
```python
@pytest.fixture
def mock_portfolio():
    portfolio = Mock(spec=Portfolio)
    # get_total_value는 메서드로 Mock 설정
    portfolio.get_total_value = Mock(return_value=10000000.0)
    portfolio.cash = 5000000.0
    portfolio.positions = {}
    return portfolio
```

### StrategyContext Mock 설정
```python
@pytest.fixture
def strategy_context():
    return StrategyContext(
        portfolio=mock_portfolio,
        data_provider=Mock(spec=IMarketDataProvider),
        logger=logging.getLogger("test"),
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        initial_capital=Decimal("10000000")
    )
```

## 🔍 예외 처리 규칙

### Signal 검증
```python
# Signal 생성 시 자동 검증됨
if not -1.0 <= self.strength <= 1.0:
    raise ValueError("Signal strength must be between -1.0 and 1.0")
```

### 전략 파라미터 검증
```python
def validate_custom_parameters(self) -> bool:
    """커스텀 파라미터 검증"""
    try:
        short_period = self.parameters.get("short_period", 20)
        long_period = self.parameters.get("long_period", 50)
        
        if short_period >= long_period:
            if self.logger:
                self.logger.error("Short period must be less than long period")
            return False
        return True
    except Exception as e:
        if self.logger:
            self.logger.error(f"Parameter validation error: {e}")
        return False
```

## 💾 데이터 타입 및 구조

### 히스토리 데이터 타입
```python
# 리스트 타입으로 통일
self.price_history: List[float] = []
self.data_history: List[MarketData] = []
self.signals_history: List[Signal] = []

# 딕셔너리 타입 (심볼별 관리 시)
self.rsi_history: Dict[str, List[float]] = {}
```

### 설정 데이터 구조
```python
# StrategyConfig 구조
@dataclass
class StrategyConfig:
    name: str
    version: str = "1.0.0"
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
```

이 명명 규칙을 따라 일관된 코드베이스를 유지하고, 새로운 전략이나 지표 개발 시 참조하여 사용합니다.