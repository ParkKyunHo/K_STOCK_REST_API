# 백테스트 엔진 사용 가이드

## 1. 개요

이 문서는 Phase 7에서 구현된 백테스트 엔진의 사용법을 설명합니다. 백테스트 엔진은 이벤트 기반 아키텍처로 설계되어 있으며, 한국 주식 시장에 특화된 거래 비용 모델을 포함합니다.

## 2. 주요 구성 요소

### 2.1 BacktestEngine
이벤트 기반 백테스트 엔진의 핵심 클래스입니다.

```python
from src.domain.backtest import BacktestEngine, BacktestConfig
from decimal import Decimal
from datetime import datetime

# 백테스트 설정
config = BacktestConfig(
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_capital=Decimal("10000000"),  # 1천만원
    commission_rate=Decimal("0.0015"),    # 0.15%
    tax_rate=Decimal("0.003"),            # 0.3% (매도세)
    slippage_rate=Decimal("0.001")        # 0.1%
)
```

### 2.2 PortfolioManager
포트폴리오 관리 및 리스크 검증을 담당합니다.

```python
from src.domain.backtest import PortfolioManager
from src.core.models.domain import Portfolio

# 포트폴리오 생성
portfolio = Portfolio(
    account_id="BACKTEST",
    initial_capital=float(config.initial_capital)
)

# 포트폴리오 매니저 초기화
portfolio_manager = PortfolioManager(portfolio, data_provider)

# 매수 주문 실행
success, message, position = await portfolio_manager.execute_buy_order(
    symbol="005930",  # 삼성전자
    quantity=100,
    price=Decimal("70000"),
    validate_risk=True  # 리스크 검증 활성화
)
```

### 2.3 PerformanceCalculator
백테스트 결과의 성과 지표를 계산합니다.

```python
from src.domain.backtest import PerformanceCalculator

calculator = PerformanceCalculator(
    initial_capital=config.initial_capital,
    portfolio_values=portfolio_values,
    daily_returns=daily_returns,
    transactions=transactions
)

# 주요 지표 계산
metrics = calculator.get_performance_metrics()
print(f"샤프 비율: {metrics.sharpe_ratio:.2f}")
print(f"최대 낙폭: {metrics.max_drawdown:.2%}")
print(f"VaR (95%): {metrics.value_at_risk_95:.2%}")
```

### 2.4 TransactionCostModel
한국 시장 특화 거래 비용 모델입니다.

```python
from src.domain.backtest import TransactionCostModel, MarketCondition

# 거래 비용 모델 생성
cost_model = TransactionCostModel(
    commission_rate=Decimal("0.0015"),
    tax_rate=Decimal("0.003"),
    market_condition=MarketCondition.SIDEWAYS
)

# 거래 비용 계산
costs = cost_model.calculate_total_cost(
    price=Decimal("70000"),
    quantity=100,
    transaction_type=TransactionType.BUY,
    instrument_type="stock"  # stock, etf, reit
)

print(f"수수료: {costs.commission:,.0f}원")
print(f"세금: {costs.tax:,.0f}원")
print(f"슬리피지: {costs.slippage:,.0f}원")
print(f"총 비용: {costs.total_cost:,.0f}원")
```

## 3. 백테스트 실행

### 3.1 기본 실행 예제

```python
async def run_backtest(strategy):
    """백테스트 실행"""
    
    # 1. 설정
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal("10000000")
    )
    
    # 2. 포트폴리오 설정
    portfolio = Portfolio(
        account_id="BACKTEST",
        initial_capital=float(config.initial_capital)
    )
    portfolio_manager = PortfolioManager(portfolio, data_provider)
    
    # 3. 엔진 생성 및 실행
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        data_provider=data_provider,
        portfolio_manager=portfolio_manager
    )
    
    # 4. 백테스트 실행
    result = await engine.run()
    
    return result
```

### 3.2 진행률 추적

```python
# 진행률 콜백 설정
engine.set_progress_callback(lambda progress: print(f"진행률: {progress:.1%}"))

# 또는 이벤트 기반
engine.progress_updated.connect(on_progress_update)
```

## 4. 성과 분석

### 4.1 수익률 지표

```python
# 총 수익률
total_return = result.total_return
print(f"총 수익률: {total_return:.2%}")

# 연환산 수익률
annualized_return = result.annualized_return
print(f"연환산 수익률: {annualized_return:.2%}")

# CAGR (연평균 성장률)
cagr = result.cagr
print(f"CAGR: {cagr:.2%}")
```

### 4.2 리스크 지표

```python
# 샤프 비율 (무위험 수익률 2% 가정)
sharpe_ratio = result.sharpe_ratio
print(f"샤프 비율: {sharpe_ratio:.2f}")

# 소르티노 비율 (하방 리스크만 고려)
sortino_ratio = result.sortino_ratio
print(f"소르티노 비율: {sortino_ratio:.2f}")

# 칼마 비율 (수익률/최대낙폭)
calmar_ratio = result.calmar_ratio
print(f"칼마 비율: {calmar_ratio:.2f}")

# 최대 낙폭
max_drawdown = result.max_drawdown
drawdown_duration = result.max_drawdown_duration
print(f"최대 낙폭: {max_drawdown:.2%} (기간: {drawdown_duration}일)")
```

### 4.3 거래 분석

```python
# 거래 통계
trade_analysis = result.trade_analysis
print(f"총 거래 횟수: {trade_analysis.total_trades}")
print(f"승률: {trade_analysis.win_rate:.1%}")
print(f"평균 수익: {trade_analysis.avg_profit:,.0f}원")
print(f"평균 손실: {trade_analysis.avg_loss:,.0f}원")
print(f"손익비: {trade_analysis.profit_factor:.2f}")

# 거래 비용 분석
cost_analysis = result.cost_analysis
print(f"총 수수료: {cost_analysis.total_commission:,.0f}원")
print(f"총 세금: {cost_analysis.total_tax:,.0f}원")
print(f"총 슬리피지: {cost_analysis.total_slippage:,.0f}원")
```

## 5. 고급 기능

### 5.1 리스크 한도 설정

```python
# 포지션 한도 설정
portfolio_manager.set_position_limits({
    "max_position_size": 0.2,      # 종목당 최대 20%
    "max_sector_exposure": 0.3,    # 섹터당 최대 30%
    "max_positions": 10            # 최대 10개 종목
})

# 리스크 검증과 함께 주문
success, message, position = await portfolio_manager.execute_buy_order(
    symbol="005930",
    quantity=1000,
    validate_risk=True  # 리스크 한도 검증
)

if not success:
    print(f"주문 실패: {message}")
```

### 5.2 시장 상황별 비용 조정

```python
# 시장 상황 설정
cost_model.update_market_condition(MarketCondition.VOLATILE)

# 시장 상황별 비용 계수
# BULL: 0.8 (20% 절감)
# BEAR: 1.2 (20% 증가)
# SIDEWAYS: 1.0 (기본)
# VOLATILE: 1.5 (50% 증가)
```

### 5.3 누진 수수료 적용

```python
# 거래 금액별 누진 수수료
costs = cost_model.calculate_commission(
    notional=Decimal("150000000"),  # 1.5억원
    use_progressive=True
)

# 수수료 구조:
# - 100만원까지: 0.2%
# - 1000만원까지: 0.15%
# - 1억원까지: 0.1%
# - 1억원 초과: 0.05%
```

## 6. 결과 시각화

### 6.1 자산 곡선

```python
import matplotlib.pyplot as plt

# 포트폴리오 가치 변화
plt.figure(figsize=(12, 6))
plt.plot(result.dates, result.portfolio_values)
plt.title("포트폴리오 가치 변화")
plt.xlabel("날짜")
plt.ylabel("포트폴리오 가치 (원)")
plt.grid(True)
plt.show()
```

### 6.2 낙폭 차트

```python
# 낙폭 계산 및 시각화
drawdowns = result.drawdown_series

plt.figure(figsize=(12, 4))
plt.fill_between(result.dates, drawdowns * 100, 0, 
                 color='red', alpha=0.3)
plt.plot(result.dates, drawdowns * 100, color='red')
plt.title("낙폭 차트")
plt.xlabel("날짜")
plt.ylabel("낙폭 (%)")
plt.grid(True)
plt.show()
```

## 7. 주의사항

1. **데이터 품질**: 백테스트 결과는 입력 데이터의 품질에 크게 의존합니다.
2. **거래 비용**: 실제 거래 비용은 증권사별로 다를 수 있습니다.
3. **슬리피지**: 대량 거래 시 시장 충격을 고려해야 합니다.
4. **과적합**: 과도한 파라미터 최적화는 실전 성과를 보장하지 않습니다.

## 8. 트러블슈팅

### 8.1 메모리 부족
대용량 데이터 처리 시 메모리 부족이 발생할 수 있습니다.

```python
# 청크 단위 처리
async for data_batch in data_provider.get_historical_data_chunked(
    symbol, start_date, end_date, chunk_size=1000
):
    # 배치 처리
    pass
```

### 8.2 성능 최적화

```python
# 벡터화 연산 활용
import numpy as np

# 느린 방법 (루프)
returns = []
for i in range(1, len(prices)):
    returns.append((prices[i] - prices[i-1]) / prices[i-1])

# 빠른 방법 (벡터화)
returns = np.diff(prices) / prices[:-1]
```

---

**작성일**: 2025-07-13  
**버전**: 1.0.0