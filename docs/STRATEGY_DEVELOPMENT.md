# 전략 개발 가이드

## 1. 개요

이 문서는 백테스팅 시스템에서 사용할 거래 전략을 개발하는 방법을 설명합니다. 플러그인 아키텍처를 통해 새로운 전략을 쉽게 추가하고 테스트할 수 있습니다.

## 2. 전략 인터페이스

### 2.1 기본 인터페이스

모든 전략은 `IStrategy` 인터페이스를 구현해야 합니다:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

class IStrategy(ABC):
    """전략 기본 인터페이스"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """전략 버전"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """전략 설명"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Parameter]:
        """전략 파라미터 정의"""
        pass
    
    @abstractmethod
    async def initialize(self, context: StrategyContext) -> None:
        """전략 초기화"""
        pass
    
    @abstractmethod
    async def on_data(self, data: MarketData) -> List[Signal]:
        """데이터 수신 시 호출"""
        pass
    
    @abstractmethod
    async def on_order_filled(self, order: Order) -> None:
        """주문 체결 시 호출"""
        pass
    
    @abstractmethod
    async def on_day_end(self) -> None:
        """일간 마감 시 호출"""
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """파라미터 유효성 검사"""
        pass
```

### 2.2 파라미터 정의

```python
from dataclasses import dataclass
from enum import Enum

class ParameterType(Enum):
    """파라미터 타입"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    ENUM = "enum"

@dataclass
class Parameter:
    """전략 파라미터"""
    name: str
    type: ParameterType
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[str]] = None
    description: str = ""
    
    def validate(self, value: Any) -> bool:
        """파라미터 값 검증"""
        if self.type == ParameterType.INT:
            if not isinstance(value, int):
                return False
            if self.min_value and value < self.min_value:
                return False
            if self.max_value and value > self.max_value:
                return False
        
        elif self.type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
            if self.min_value and value < self.min_value:
                return False
            if self.max_value and value > self.max_value:
                return False
        
        elif self.type == ParameterType.ENUM:
            if self.choices and value not in self.choices:
                return False
        
        return True
```

## 3. 전략 컨텍스트

### 3.1 StrategyContext 클래스

```python
@dataclass
class StrategyContext:
    """전략 실행 컨텍스트"""
    portfolio: Portfolio
    data_provider: IMarketDataProvider
    order_manager: OrderManager
    risk_manager: RiskManager
    logger: logging.Logger
    
    # 백테스트 설정
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission_rate: float = 0.00015
    slippage_rate: float = 0.0001
    
    # 실행 모드
    is_live: bool = False
    is_paper_trading: bool = False
    
    def get_current_positions(self) -> Dict[str, Position]:
        """현재 포지션 조회"""
        return self.portfolio.positions
    
    def get_account_value(self) -> float:
        """계좌 가치 조회"""
        return self.portfolio.get_total_value()
    
    async def get_historical_data(
        self,
        symbol: str,
        lookback_days: int
    ) -> pd.DataFrame:
        """과거 데이터 조회"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        return await self.data_provider.get_ohlcv(
            symbol, "1d", start_date, end_date
        )
```

### 3.2 시장 데이터 모델

```python
@dataclass
class MarketData:
    """시장 데이터"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    # 추가 정보
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }
```

## 4. 신호 및 주문

### 4.1 신호 타입

```python
from enum import Enum

class SignalType(Enum):
    """신호 타입"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"
    CLOSE_ALL = "close_all"

@dataclass
class Signal:
    """거래 신호"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    strength: float  # -1.0 ~ 1.0
    quantity: Optional[int] = None
    price: Optional[float] = None
    reason: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # 신호 강도 검증
        if not -1.0 <= self.strength <= 1.0:
            raise ValueError("Signal strength must be between -1.0 and 1.0")
```

### 4.2 주문 생성

```python
class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class OrderRequest:
    """주문 요청"""
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"  # day, gtc, ioc, fok
    
    def validate(self) -> bool:
        """주문 유효성 검사"""
        if self.quantity <= 0:
            return False
        
        if self.order_type == OrderType.LIMIT and not self.price:
            return False
        
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if not self.stop_price:
                return False
        
        return True
```

## 5. 전략 예제

### 5.1 이동평균 크로스오버 전략

```python
class MovingAverageCrossover(IStrategy):
    """이동평균 크로스오버 전략"""
    
    @property
    def name(self) -> str:
        return "MA Crossover"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "단기/장기 이동평균 크로스오버 전략"
    
    @property
    def parameters(self) -> Dict[str, Parameter]:
        return {
            "short_period": Parameter(
                name="short_period",
                type=ParameterType.INT,
                default=20,
                min_value=5,
                max_value=50,
                description="단기 이동평균 기간"
            ),
            "long_period": Parameter(
                name="long_period",
                type=ParameterType.INT,
                default=50,
                min_value=20,
                max_value=200,
                description="장기 이동평균 기간"
            ),
            "position_size": Parameter(
                name="position_size",
                type=ParameterType.FLOAT,
                default=0.95,
                min_value=0.1,
                max_value=1.0,
                description="포지션 크기 (자본 대비 비율)"
            )
        }
    
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.short_ma = []
        self.long_ma = []
        self.price_history = []
        self.position = None
    
    async def initialize(self, context: StrategyContext) -> None:
        """전략 초기화"""
        self.context = context
        self.logger = context.logger
        
        # 파라미터 검증
        if not self.validate_parameters():
            raise ValueError("Invalid parameters")
        
        self.logger.info(f"Initialized {self.name} with params: {self.params}")
    
    async def on_data(self, data: MarketData) -> List[Signal]:
        """데이터 수신 시 신호 생성"""
        signals = []
        
        # 가격 이력 업데이트
        self.price_history.append(data.close)
        
        # 이동평균 계산
        if len(self.price_history) >= self.params["long_period"]:
            self.short_ma = np.mean(
                self.price_history[-self.params["short_period"]:]
            )
            self.long_ma = np.mean(
                self.price_history[-self.params["long_period"]:]
            )
            
            # 크로스오버 확인
            prev_short = np.mean(
                self.price_history[-self.params["short_period"]-1:-1]
            )
            prev_long = np.mean(
                self.price_history[-self.params["long_period"]-1:-1]
            )
            
            # 골든 크로스 (매수 신호)
            if prev_short <= prev_long and self.short_ma > self.long_ma:
                if not self.position:
                    signal = Signal(
                        timestamp=data.timestamp,
                        symbol=data.symbol,
                        signal_type=SignalType.BUY,
                        strength=1.0,
                        reason="Golden Cross"
                    )
                    signals.append(signal)
            
            # 데드 크로스 (매도 신호)
            elif prev_short >= prev_long and self.short_ma < self.long_ma:
                if self.position:
                    signal = Signal(
                        timestamp=data.timestamp,
                        symbol=data.symbol,
                        signal_type=SignalType.SELL,
                        strength=1.0,
                        reason="Death Cross"
                    )
                    signals.append(signal)
        
        return signals
    
    async def on_order_filled(self, order: Order) -> None:
        """주문 체결 시 호출"""
        if order.side == "buy":
            self.position = order
            self.logger.info(f"Position opened: {order}")
        else:
            self.position = None
            self.logger.info(f"Position closed: {order}")
    
    async def on_day_end(self) -> None:
        """일간 마감 처리"""
        pass
    
    def validate_parameters(self) -> bool:
        """파라미터 유효성 검사"""
        short = self.params.get("short_period", 20)
        long = self.params.get("long_period", 50)
        
        if short >= long:
            self.logger.error("Short period must be less than long period")
            return False
        
        return True
```

### 5.2 RSI 전략

```python
class RSIStrategy(IStrategy):
    """RSI 기반 전략"""
    
    @property
    def name(self) -> str:
        return "RSI Strategy"
    
    @property
    def parameters(self) -> Dict[str, Parameter]:
        return {
            "rsi_period": Parameter(
                name="rsi_period",
                type=ParameterType.INT,
                default=14,
                min_value=5,
                max_value=30,
                description="RSI 계산 기간"
            ),
            "oversold_threshold": Parameter(
                name="oversold_threshold",
                type=ParameterType.FLOAT,
                default=30.0,
                min_value=10.0,
                max_value=40.0,
                description="과매도 임계값"
            ),
            "overbought_threshold": Parameter(
                name="overbought_threshold",
                type=ParameterType.FLOAT,
                default=70.0,
                min_value=60.0,
                max_value=90.0,
                description="과매수 임계값"
            )
        }
    
    def calculate_rsi(self, prices: pd.Series) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(
            window=self.params["rsi_period"]
        ).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(
            window=self.params["rsi_period"]
        ).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
```

## 6. 지표 라이브러리

### 6.1 기술적 지표 인터페이스

```python
class IIndicator(ABC):
    """지표 인터페이스"""
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """지표 계산"""
        pass
    
    @property
    @abstractmethod
    def required_periods(self) -> int:
        """필요한 최소 데이터 기간"""
        pass
```

### 6.2 지표 구현 예제

```python
class BollingerBands(IIndicator):
    """볼린저 밴드"""
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """볼린저 밴드 계산"""
        close = data["close"]
        
        # 중심선 (SMA)
        middle = close.rolling(window=self.period).mean()
        
        # 표준편차
        std = close.rolling(window=self.period).std()
        
        # 상단/하단 밴드
        upper = middle + (std * self.num_std)
        lower = middle - (std * self.num_std)
        
        return pd.DataFrame({
            "bb_middle": middle,
            "bb_upper": upper,
            "bb_lower": lower,
            "bb_width": upper - lower,
            "bb_percent": (close - lower) / (upper - lower)
        })
    
    @property
    def required_periods(self) -> int:
        return self.period

class MACD(IIndicator):
    """MACD"""
    
    def __init__(
        self, 
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        close = data["close"]
        
        # EMA 계산
        ema_fast = close.ewm(span=self.fast_period).mean()
        ema_slow = close.ewm(span=self.slow_period).mean()
        
        # MACD 라인
        macd_line = ema_fast - ema_slow
        
        # 시그널 라인
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        
        # 히스토그램
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram
        })
```

## 7. 백테스트 통합

### 7.1 백테스트 엔진과의 통합 (Phase 7 구현 완료)

```python
from src.domain.backtest import BacktestEngine, BacktestConfig
from src.domain.backtest import PortfolioManager, TransactionCostModel
from decimal import Decimal
from datetime import datetime

async def run_strategy_backtest(strategy: IStrategy):
    """전략 백테스트 실행"""
    
    # 백테스트 설정
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal("10000000"),
        commission_rate=Decimal("0.0015"),  # 0.15%
        tax_rate=Decimal("0.003"),          # 0.3% (매도시)
        slippage_rate=Decimal("0.001")      # 0.1%
    )
    
    # 포트폴리오 매니저 생성
    portfolio = Portfolio(
        account_id="BACKTEST",
        initial_capital=float(config.initial_capital)
    )
    portfolio_manager = PortfolioManager(portfolio, data_provider)
    
    # 백테스트 엔진 생성
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        data_provider=data_provider,
        portfolio_manager=portfolio_manager
    )
    
    # 백테스트 실행
    result = await engine.run()
    
    # 결과 분석
    print(f"총 수익률: {result.total_return:.2%}")
    print(f"연환산 수익률: {result.annualized_return:.2%}")
    print(f"샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"최대 낙폭: {result.max_drawdown:.2%}")
    print(f"승률: {result.win_rate:.1%}")
    
    return result
```

### 7.2 성과 분석

백테스트 결과는 다음과 같은 주요 지표를 포함합니다:

- **수익률 지표**
  - 총 수익률 (Total Return)
  - 연환산 수익률 (Annualized Return)
  - 월별/일별 수익률

- **리스크 지표**
  - 샤프 비율 (Sharpe Ratio)
  - 소르티노 비율 (Sortino Ratio)
  - 칼마 비율 (Calmar Ratio)
  - 최대 낙폭 (Maximum Drawdown)
  - VaR (Value at Risk)
  - CVaR (Conditional VaR)

- **거래 분석**
  - 총 거래 횟수
  - 승률 (Win Rate)
  - 평균 수익/손실
  - 손익비 (Profit Factor)
  - 거래 비용 분석

### 7.3 전략 로더

```python
class StrategyLoader:
    """전략 동적 로더"""
    
    def __init__(self, strategy_dir: str = "plugins/strategies"):
        self.strategy_dir = strategy_dir
        self.strategies = {}
        
    def load_all_strategies(self) -> Dict[str, Type[IStrategy]]:
        """모든 전략 로드"""
        for file in Path(self.strategy_dir).glob("*.py"):
            if file.name.startswith("_"):
                continue
            
            try:
                strategy_class = self._load_strategy_from_file(file)
                if strategy_class:
                    self.strategies[strategy_class.name] = strategy_class
            except Exception as e:
                logger.error(f"Failed to load strategy from {file}: {e}")
        
        return self.strategies
    
    def _load_strategy_from_file(self, file_path: Path) -> Optional[Type[IStrategy]]:
        """파일에서 전략 클래스 로드"""
        spec = importlib.util.spec_from_file_location(
            file_path.stem, 
            file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # IStrategy 구현 찾기
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, IStrategy) and 
                obj != IStrategy):
                return obj
        
        return None
```

### 7.2 전략 실행기

```python
class StrategyRunner:
    """전략 실행기"""
    
    def __init__(
        self,
        strategy: IStrategy,
        context: StrategyContext
    ):
        self.strategy = strategy
        self.context = context
        self.active = False
    
    async def run(self, data_stream: AsyncIterator[MarketData]):
        """전략 실행"""
        self.active = True
        
        # 전략 초기화
        await self.strategy.initialize(self.context)
        
        try:
            async for data in data_stream:
                if not self.active:
                    break
                
                # 신호 생성
                signals = await self.strategy.on_data(data)
                
                # 신호 처리
                for signal in signals:
                    await self._process_signal(signal)
            
            # 마감 처리
            await self.strategy.on_day_end()
            
        except Exception as e:
            self.context.logger.exception(f"Strategy error: {e}")
            raise
    
    async def _process_signal(self, signal: Signal):
        """신호 처리"""
        # 리스크 검사
        if not await self._check_risk(signal):
            return
        
        # 주문 생성
        order = self._create_order_from_signal(signal)
        
        # 주문 실행
        if order:
            result = await self.context.order_manager.submit_order(order)
            if result.status == "filled":
                await self.strategy.on_order_filled(result)
```

## 8. UI 통합 (Phase 8 - 진행 중)

### 8.1 전략 UI 통합

Trading UI에서 전략을 관리하고 실행할 수 있습니다:

```python
# UI에서 전략 로드
from src.presentation.ui.widgets import StrategyListWidget

# 전략 목록 위젯
strategy_widget = StrategyListWidget()
strategy_widget.load_strategies(available_strategies)

# 전략 선택 시 이벤트
strategy_widget.strategy_double_clicked.connect(
    lambda strategy: self.open_strategy_config(strategy)
)

# 백테스트 실행
async def on_run_backtest():
    strategy = strategy_widget.get_selected_strategy()
    config = backtest_config_widget.get_config()
    
    # 진행률 표시
    progress_widget.show()
    
    # 백테스트 실행
    result = await run_strategy_backtest(strategy)
    
    # 결과 표시
    metrics_table.update_metrics(result)
    equity_curve.update_chart(result.portfolio_values)
```

### 8.2 전략 설정 다이얼로그

```python
class StrategyConfigDialog(QDialog):
    """전략 파라미터 설정 다이얼로그"""
    
    def __init__(self, strategy: IStrategy):
        super().__init__()
        self.strategy = strategy
        self._create_ui()
    
    def _create_ui(self):
        layout = QFormLayout()
        
        # 전략 파라미터별 입력 위젯 생성
        for name, param in self.strategy.parameters.items():
            widget = self._create_param_widget(param)
            layout.addRow(param.description, widget)
```

## 9. 전략 테스트

### 9.1 단위 테스트

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_ma_crossover_strategy():
    """이동평균 크로스오버 전략 테스트"""
    # 전략 생성
    params = {
        "short_period": 10,
        "long_period": 20,
        "position_size": 0.95
    }
    strategy = MovingAverageCrossover(params)
    
    # Mock 컨텍스트
    context = Mock(spec=StrategyContext)
    context.logger = logging.getLogger("test")
    
    # 초기화
    await strategy.initialize(context)
    
    # 테스트 데이터 생성
    test_data = []
    for i in range(30):
        price = 100 + i + np.sin(i * 0.5) * 5
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now() + timedelta(days=i),
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=1000000
        )
        test_data.append(data)
    
    # 신호 생성 테스트
    signals_generated = []
    for data in test_data:
        signals = await strategy.on_data(data)
        signals_generated.extend(signals)
    
    # 검증
    assert len(signals_generated) > 0
    assert all(isinstance(s, Signal) for s in signals_generated)
```

### 8.2 통합 테스트

```python
class StrategyBacktestTest:
    """전략 백테스트 통합 테스트"""
    
    async def test_strategy_with_historical_data(self):
        """과거 데이터로 전략 테스트"""
        # 데이터 로드
        data = pd.read_csv("test_data/AAPL_2020_2021.csv")
        
        # 백테스터 설정
        backtester = Backtester(
            initial_capital=100000,
            commission_rate=0.001
        )
        
        # 전략 실행
        strategy = MovingAverageCrossover({
            "short_period": 20,
            "long_period": 50
        })
        
        results = await backtester.run(strategy, data)
        
        # 성과 검증
        assert results.total_return > -0.5  # 50% 이상 손실 없음
        assert results.sharpe_ratio > 0     # 양의 샤프 비율
        assert results.max_drawdown < 0.3   # 최대 낙폭 30% 이하
```

## 9. 전략 최적화

### 9.1 파라미터 최적화

```python
class StrategyOptimizer:
    """전략 파라미터 최적화"""
    
    def __init__(self, strategy_class: Type[IStrategy]):
        self.strategy_class = strategy_class
        self.results = []
    
    async def optimize(
        self,
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        metric: str = "sharpe_ratio"
    ) -> Dict[str, Any]:
        """그리드 서치 최적화"""
        # 파라미터 조합 생성
        param_combinations = self._generate_param_combinations(param_grid)
        
        # 병렬 백테스트
        tasks = []
        for params in param_combinations:
            task = self._backtest_with_params(params, data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # 최적 파라미터 찾기
        best_result = max(results, key=lambda x: x[metric])
        
        return {
            "best_params": best_result["params"],
            "best_metric": best_result[metric],
            "all_results": results
        }
    
    def _generate_param_combinations(
        self, 
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """파라미터 조합 생성"""
        from itertools import product
        
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        
        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations
```

### 9.2 Walk-Forward 분석

```python
class WalkForwardAnalysis:
    """Walk-Forward 분석"""
    
    def __init__(
        self,
        strategy_class: Type[IStrategy],
        optimization_window: int = 252,  # 1년
        test_window: int = 63            # 3개월
    ):
        self.strategy_class = strategy_class
        self.optimization_window = optimization_window
        self.test_window = test_window
    
    async def run(
        self,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Walk-Forward 분석 실행"""
        results = []
        
        # 시간 윈도우 이동
        for i in range(0, len(data) - self.optimization_window - self.test_window):
            # 최적화 기간
            opt_start = i
            opt_end = i + self.optimization_window
            opt_data = data.iloc[opt_start:opt_end]
            
            # 테스트 기간
            test_start = opt_end
            test_end = test_start + self.test_window
            test_data = data.iloc[test_start:test_end]
            
            # 파라미터 최적화
            optimizer = StrategyOptimizer(self.strategy_class)
            best_params = await optimizer.optimize(param_grid, opt_data)
            
            # 테스트 기간 백테스트
            strategy = self.strategy_class(best_params["best_params"])
            test_result = await self._backtest(strategy, test_data)
            
            results.append({
                "optimization_period": (opt_start, opt_end),
                "test_period": (test_start, test_end),
                "best_params": best_params["best_params"],
                "test_performance": test_result
            })
        
        return results
```

## 10. 전략 배포

### 10.1 전략 패키징

```python
# strategy_template.py
"""
전략 템플릿
"""

from typing import Dict, Any
from strategy_base import IStrategy, Signal, MarketData

class MyCustomStrategy(IStrategy):
    """사용자 정의 전략"""
    
    # 메타데이터
    META = {
        "author": "Your Name",
        "version": "1.0.0",
        "tags": ["momentum", "trend"],
        "markets": ["stocks", "crypto"],
        "timeframes": ["1d", "4h", "1h"]
    }
    
    @property
    def name(self) -> str:
        return "My Custom Strategy"
    
    # ... 구현 ...

# 전략 등록
def register():
    """전략 등록 함수"""
    return MyCustomStrategy
```

### 10.2 전략 검증

```python
class StrategyValidator:
    """전략 검증기"""
    
    def validate(self, strategy_class: Type[IStrategy]) -> bool:
        """전략 유효성 검사"""
        # 필수 메서드 확인
        required_methods = [
            "name", "version", "parameters",
            "initialize", "on_data", "on_order_filled"
        ]
        
        for method in required_methods:
            if not hasattr(strategy_class, method):
                logger.error(f"Missing required method: {method}")
                return False
        
        # 파라미터 검증
        try:
            strategy = strategy_class({})
            params = strategy.parameters
            
            for name, param in params.items():
                if not isinstance(param, Parameter):
                    logger.error(f"Invalid parameter: {name}")
                    return False
        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return False
        
        return True
```

---

**버전**: 1.0.0  
**작성일**: 2024-01-12  
**작성자**: Strategy Development Team