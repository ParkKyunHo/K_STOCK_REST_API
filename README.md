# 키움증권 REST API 백테스팅 시스템

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

키움증권 REST API를 활용한 확장 가능한 주식 거래 전략 백테스팅 시스템입니다.

## 🚀 주요 기능

- **178개 키움증권 REST API 완벽 지원**
- **플러그인 기반 전략 시스템**
- **실시간 데이터 처리 (WebSocket)**
- **이벤트 기반 백테스트 엔진** ✅
  - 비동기 처리로 빠른 실행
  - 실시간 진행률 추적
  - 상세한 거래 내역 기록
- **포트폴리오 및 리스크 관리** ✅
  - 포지션 한도 및 섹터 집중도 관리
  - 실시간 평가 및 성과 추적
- **한국 시장 특화 거래 비용 모델** ✅
  - 증권거래세, 수수료 정확한 계산
  - 슬리피지 및 시장 충격 모델링
- **성과 지표 계산** ✅
  - Sharpe, Sortino, Calmar 비율
  - VaR, CVaR, 최대 낙폭
- **PyQt5 기반 Trading UI** 🔄
  - 다크 테마 적용
  - 전략 관리 및 백테스트 실행
- **확장 가능한 아키텍처**

## 📋 요구사항

- Python 3.9 이상
- Windows 10/11 (키움증권 API 지원)
- 키움증권 REST API 계정

## 🛠️ 설치

### 1. 리포지토리 클론

```bash
git clone https://github.com/ParkKyunHo/K_STOCK_REST_API.git
cd K_STOCK_REST_API
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키 설정
```

## 🚦 빠른 시작

### 기본 사용법

```python
from src.infrastructure.api import ClientFactory
from src.domain.backtest import BacktestEngine, BacktestConfig
from src.domain.strategies import MovingAverageCrossover
from decimal import Decimal
from datetime import datetime

# API 클라이언트 초기화 (환경에 따라 자동 선택)
client = ClientFactory.create_client()

# 전략 생성
strategy = MovingAverageCrossover({
    "short_period": 20,
    "long_period": 50,
    "position_size": 0.95
})

# 백테스트 설정
config = BacktestConfig(
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_capital=Decimal("10000000"),
    commission_rate=Decimal("0.0015"),  # 0.15%
    tax_rate=Decimal("0.003")           # 0.3%
)

# 백테스트 실행
engine = BacktestEngine(config, strategy, data_provider, portfolio_manager)
results = await engine.run()

# 결과 출력
print(f"총 수익률: {results.total_return:.2%}")
print(f"샤프 비율: {results.sharpe_ratio:.2f}")
print(f"최대 낙폭: {results.max_drawdown:.2%}")
print(f"승률: {results.win_rate:.1%}")
```

### UI 실행

```bash
# Trading UI 실행
python run_trading_ui.py

# 또는
python -m src.presentation.ui.application

# 테스트 UI (샘플 데이터 포함)
python test_ui.py
```

## 📁 프로젝트 구조

```
K_STOCK_REST_API/
├── docs/                    # 문서
│   ├── ARCHITECTURE.md     # 시스템 아키텍처
│   ├── API_INTEGRATION.md  # API 통합 가이드
│   └── ...
├── src/                    # 소스 코드
│   ├── core/              # 핵심 인터페이스
│   ├── infrastructure/    # 인프라 계층
│   ├── domain/           # 도메인 로직
│   ├── application/      # 애플리케이션 서비스
│   └── presentation/     # UI 계층
├── tests/                 # 테스트
├── plugins/              # 플러그인
│   ├── strategies/      # 전략 플러그인
│   └── indicators/      # 지표 플러그인
└── config/              # 설정 파일
```

## 🔌 전략 개발

새로운 전략을 개발하려면 `IStrategy` 인터페이스를 구현하세요:

```python
from src.core.interfaces import IStrategy, Signal, MarketData

class MyStrategy(IStrategy):
    @property
    def name(self) -> str:
        return "My Custom Strategy"
    
    async def on_data(self, data: MarketData) -> List[Signal]:
        # 전략 로직 구현
        if self.should_buy(data):
            return [Signal(
                symbol=data.symbol,
                signal_type=SignalType.BUY,
                strength=1.0
            )]
        return []
```

자세한 내용은 [전략 개발 가이드](docs/STRATEGY_DEVELOPMENT.md)를 참조하세요.

## 📊 지원 API

### 주요 API 카테고리

- **인증**: OAuth2 토큰 관리
- **시세 조회**: 실시간/과거 가격 데이터
- **주문 실행**: 매수/매도/정정/취소
- **계좌 관리**: 잔고, 거래내역 조회
- **실시간 데이터**: WebSocket 스트리밍

전체 API 목록은 [API 통합 가이드](docs/API_INTEGRATION.md)를 참조하세요.

## 🧪 테스트

```bash
# 단위 테스트
pytest tests/unit

# 통합 테스트
pytest tests/integration

# UI 테스트 (헤드리스 모드)
QT_QPA_PLATFORM=offscreen pytest tests/unit/presentation

# 커버리지 리포트
pytest --cov=src tests/
```

## 📈 프로젝트 진행 상황

**전체 진행률**: 60% (2025-07-13 기준)

- ✅ Phase 1-6: 기본 인프라 및 데이터 수집 (100%)
- ✅ Phase 7: 백테스트 엔진 개발 (100%)
- 🔄 Phase 8: Trading UI 개발 (25%)
- ⏳ Phase 9-12: 전략 시스템, 리스크 관리, 최적화 등

자세한 진행 상황은 [PROJECT_STATUS.md](docs/PROJECT_STATUS.md)를 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

코딩 표준은 [CODING_STANDARDS.md](docs/CODING_STANDARDS.md)를 참조하세요.

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

- **개발자**: Park Kyun Ho
- **GitHub**: [@ParkKyunHo](https://github.com/ParkKyunHo)
- **Email**: your.email@example.com

## 🙏 감사의 말

- 키움증권 OpenAPI 팀
- 오픈소스 커뮤니티

---

**⚠️ 주의사항**: 이 시스템은 교육 및 연구 목적으로 개발되었습니다. 실제 거래에 사용하기 전에 충분한 테스트와 검증을 거치시기 바랍니다. 투자 손실에 대한 책임은 사용자 본인에게 있습니다.