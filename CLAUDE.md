# 키움증권 REST API 백테스팅 시스템 - AI 어시스턴트 가이드

## 🎯 프로젝트 개요

이 프로젝트는 키움증권 REST API를 활용한 확장 가능한 자동화 백테스팅 시스템입니다. Python 기반으로 개발되며, 플러그인 아키텍처를 통해 다양한 전략과 데이터 소스를 지원합니다.

### 핵심 목표
- 전략별 백테스트 자동화
- 관심 종목 및 전체 시장 분석
- 실시간 데이터 처리 및 시각화
- 확장 가능한 플러그인 시스템

## 📁 프로젝트 구조

```
K_STOCK_REST_API/
├── CLAUDE.md                    # 이 문서 (AI 가이드)
├── requirements.txt             # 의존성 패키지
├── setup.py                     # 패키지 설정
├── .env.example                 # 환경변수 예시
├── docs/                        # 문서
│   ├── ARCHITECTURE.md         # 시스템 아키텍처
│   ├── CODING_STANDARDS.md     # 코딩 표준
│   ├── API_INTEGRATION.md      # API 통합 가이드
│   ├── STRATEGY_DEVELOPMENT.md # 전략 개발 가이드
│   ├── WORKFLOW.md            # 작업 프로세스 가이드
│   └── PROJECT_STATUS.md      # 프로젝트 상태
├── src/                         # 소스 코드
│   ├── __init__.py
│   ├── core/                   # 핵심 모듈
│   │   ├── __init__.py
│   │   ├── interfaces/         # 인터페이스 정의
│   │   ├── models/            # 도메인 모델
│   │   └── exceptions/        # 커스텀 예외
│   ├── infrastructure/         # 인프라 계층
│   │   ├── __init__.py
│   │   ├── api/              # API 클라이언트
│   │   ├── cache/            # 캐싱 시스템
│   │   └── database/         # 데이터베이스
│   ├── domain/                # 도메인 계층
│   │   ├── __init__.py
│   │   ├── strategy/         # 전략 엔진
│   │   ├── portfolio/        # 포트폴리오 관리
│   │   └── risk/            # 리스크 관리
│   ├── application/          # 애플리케이션 계층
│   │   ├── __init__.py
│   │   ├── backtest/        # 백테스트 컨트롤러
│   │   └── services/        # 비즈니스 서비스
│   ├── presentation/        # 프레젠테이션 계층
│   │   ├── __init__.py
│   │   ├── ui/            # PyQt5 UI
│   │   └── api/           # REST API (선택)
│   └── plugins/            # 플러그인
│       ├── __init__.py
│       ├── strategies/    # 전략 플러그인
│       └── indicators/    # 지표 플러그인
├── tests/                  # 테스트
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/               # 유틸리티 스크립트
├── data/                 # 데이터 저장소
│   ├── cache/
│   └── results/
└── config/              # 설정 파일
    ├── config.yaml
    └── logging.yaml
```

## 🔧 현재 상태

### 완료된 작업
- [x] 키움증권 REST API 명세서 분석 (178개 API)
- [x] TSD (기술 명세서) 작성
- [x] 프로젝트 구조 설계
- [x] 핵심 문서 작성 완료
- [x] Phase 2: 기본 프로젝트 구조 생성
  - 디렉토리 구조 및 패키지 설정
  - 의존성 및 설정 파일 생성
  - 로깅 및 테스트 프레임워크 설정
- [x] 작업 프로세스 문서화 (WORKFLOW.md)
- [x] Phase 3: 핵심 인터페이스 정의
  - IStrategy, IMarketDataProvider, IOrderManager, IRiskManager
  - Position, Transaction, Portfolio, Account 도메인 모델
- [x] Phase 4: 인증 시스템 구현
  - OAuth2Manager: 토큰 자동 관리
  - CredentialManager: 암호화된 자격증명 저장
  - AuthenticationService: 통합 인증 서비스
- [x] Phase 5: API 클라이언트 개발
  - KiwoomAPIClient: REST API 클라이언트
  - Rate Limiting 및 재시도 로직
  - Mock 클라이언트 (96.74% 커버리지)
  - ClientFactory: 환경별 자동 설정
- [x] Phase 6: 데이터 수집 모듈 개발
  - MarketData 모델 (88.36% 커버리지)
  - KiwoomMarketDataProvider (70.59% 커버리지)
  - DataNormalizer: API 응답 정규화

### 진행 중
- [ ] Phase 7: 백테스트 엔진 개발

### 다음 단계
1. 이벤트 기반 백테스터 구현
2. 포트폴리오 관리자 개발
3. 성과 지표 계산기
4. 거래 비용 모델

## 📝 코딩 규칙 요약

### 1. 일반 규칙
- Python 3.9+ 사용
- 타입 힌팅 필수
- PEP 8 준수
- 모든 공개 함수/클래스에 docstring 작성

### 2. 명명 규칙
```python
# 클래스: PascalCase
class MarketDataProvider:
    pass

# 함수/변수: snake_case
def calculate_returns(prices: pd.Series) -> pd.Series:
    pass

# 상수: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 인터페이스: I 접두사
class IStrategy(ABC):
    pass
```

### 3. 비동기 프로그래밍
```python
# 비동기 함수는 async 접두사 사용
async def fetch_market_data(symbol: str) -> pd.DataFrame:
    pass

# 컨텍스트 매니저 사용
async with session.get(url) as response:
    data = await response.json()
```

### 4. 에러 처리
```python
# 구체적인 예외 사용
try:
    result = await api_client.request(api_id, params)
except APIError as e:
    logger.error(f"API error: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise SystemError(f"System error: {e}")
```

## 🔑 주요 API 정보

### 인증
- `au10001`: 접근토큰 발급
- `au10002`: 접근토큰 폐기

### 시세 데이터
- `ka10079`: 틱 차트
- `ka10080`: 분봉 차트
- `ka10081`: 일봉 차트
- `ka10082`: 주봉 차트
- `ka10083`: 월봉 차트

### 종목 정보
- `ka10001`: 주식 기본정보
- `ka10095`: 관심종목 정보
- `ka10099`: 종목정보 리스트

### 주문 실행
- `kt10000`: 주식 매수
- `kt10001`: 주식 매도
- `kt10002`: 주문 정정
- `kt10003`: 주문 취소

## 🔄 표준 작업 프로세스

### 필수 작업 순서
모든 작업은 반드시 다음 순서를 따라야 합니다:

1. **작업 계획**
   - TodoWrite로 작업 목록 생성
   - 관련 문서 검토

2. **테스트 우선 개발 (TDD)**
   ```bash
   # 1. 테스트 작성
   # 2. 구현
   # 3. 테스트 실행
   pytest tests/unit/test_feature.py -v
   ```

3. **테스트 결과 확인**
   - ✅ 성공 → 문서 업데이트
   - ❌ 실패 → 오류 수정 → 재테스트

4. **문서 업데이트**
   - PROJECT_STATUS.md 진행률 업데이트
   - 관련 기술 문서 업데이트
   - 변경 이력 기록

### 체크리스트
- [ ] 가상환경 활성화 확인
- [ ] 테스트 먼저 작성
- [ ] 모든 테스트 통과
- [ ] 코드 스타일 검사 (black, isort, flake8)
- [ ] 타입 체크 (mypy)
- [ ] 문서 업데이트 완료

자세한 내용은 [WORKFLOW.md](docs/WORKFLOW.md) 참조

## 🚀 작업 시작 시 체크리스트

⚠️ **중요**: 모든 작업은 반드시 가상환경에서 실행해야 합니다!

1. **환경 확인**
   - **필수** Python 가상환경 활성화: `source venv/bin/activate`
   - 가상환경 활성화 확인: 터미널 프롬프트에 `(venv)` 표시
   - 의존성 설치 확인: `pip list`

2. **코드 작성 전**
   - 관련 인터페이스 확인
   - 기존 코드 패턴 참고
   - 테스트 케이스 먼저 작성 (TDD)

3. **코드 작성 중**
   - 타입 힌팅 확인
   - 에러 처리 추가
   - 로깅 추가

4. **코드 작성 후**
   - 유닛 테스트 실행
   - 코드 포맷팅 (`black`)
   - 타입 체크 (`mypy`)
   - 린트 실행 (`pylint`)

## 🎯 현재 작업 중인 내용

**작업 ID**: INIT-008
**작업 내용**: Trading UI 개발 (Phase 8)
**상태**: 진행 중 (25%)

### 완료된 작업 (Phase 7 - 백테스트 엔진)
✅ **백테스트 엔진 개발 완료** (100%)
1. **BacktestEngine**: 이벤트 기반 백테스터
   - 비동기 이벤트 루프 처리
   - 전략 신호 실행 및 포트폴리오 업데이트
   - 실시간 진행률 추적
   - 백테스트 결과 생성 및 분석

2. **PortfolioManager**: 포트폴리오 관리자
   - 포지션 추적 및 관리
   - 리스크 검증 (포지션 한도, 섹터 집중도)
   - 실시간 평가 및 성과 계산
   - 주문 실행 및 거래 기록

3. **PerformanceCalculator**: 성과 지표 계산기
   - Sharpe, Sortino, Calmar 비율
   - 최대 낙폭 및 회복 기간
   - VaR, CVaR 리스크 지표
   - 승률 및 손익비 분석

4. **TransactionCostModel**: 거래 비용 모델
   - 한국 시장 특화 수수료 구조
   - 누진 수수료 및 세금 계산
   - 슬리피지 및 시장 충격 모델
   - 시간대별/시장 상황별 비용 조정

### 진행 중인 작업 (Phase 8 - Trading UI)
🔄 **Trading UI 개발** (25%)
1. ✅ PyQt5 어플리케이션 프레임워크
2. ✅ 메인 윈도우 및 메뉴 시스템
3. ✅ 전략 목록 위젯
4. 🔄 전략 설정 다이얼로그 (다음)
5. ⏳ 백테스트 진행 표시
6. ⏳ 차트 및 시각화

## 📌 중요 참고사항

1. **가상환경 사용 필수**
   - 모든 Python 명령은 가상환경 내에서 실행
   - 패키지 설치는 항상 `pip install` 사용 (시스템 Python 오염 방지)
   - 가상환경 미사용 시 의존성 충돌 및 버전 문제 발생 가능

2. **API 제한사항**
   - Rate Limit: 초당 10회
   - 일일 호출 한도 있음
   - 실시간 데이터는 WebSocket 사용

3. **데이터 캐싱**
   - 과거 데이터는 로컬 캐시 우선
   - 캐시 만료 시간 설정 필요
   - 대용량 데이터는 청크 단위 처리

4. **WSL2 GUI 실행**
   - WSL2 환경에서 Trading UI 실행 시 X11 서버 필요
   - VcXsrv 설정: "Disable access control" 필수 체크
   - DISPLAY 설정: `export DISPLAY=$(ip route show | grep -i default | awk '{ print $3 }'):0`
   - 한글 폰트: `sudo apt-get install fonts-noto-cjk fonts-nanum fonts-nanum-coding`
   - 자세한 설정: [WSL2_SETUP.md](docs/WSL2_SETUP.md) 참조

5. **보안**
   - API 키는 환경변수로 관리
   - 민감 정보는 절대 커밋하지 않음
   - 로그에 개인정보 포함 금지

6. **UI 개발 (PyQt5)**
   - 헤드리스 환경에서 테스트 시: `QT_QPA_PLATFORM=offscreen`
   - 모든 QDockWidget과 QToolBar에 objectName 설정 필수
   - 한글 폰트 설정: 시스템별 폰트 자동 감지 및 설정
   - Widget import는 모듈 레벨에서만 수행
   - UI 실행: `python run_trading_ui.py`
   - 테스트 UI: `python test_ui.py`
   - 다크 테마 적용됨 (금융 애플리케이션에 최적화)
   
   **WSL2 환경에서 GUI 실행**:
   - VcXsrv 설치 및 설정 필요
   - 설정 파일 저장: `C:\Users\[사용자명]\Documents\vcxsrv.xlaunch`
   - WSL2 실행 스크립트: `./run_trading_ui_wsl.sh`
   - Offscreen 모드: `./run_ui_offscreen.sh`
   - 상세 설정: `docs/WSL2_SETUP.md` 참조
   
   **⚠️ PyQt5 위젯 objectName 설정 필수**:
   ```python
   # 모든 QDockWidget, QToolBar, 주요 위젯에 objectName 설정
   self.strategy_dock = QDockWidget("전략 목록", self)
   self.strategy_dock.setObjectName("strategyDock")  # 필수!
   
   self.main_toolbar = self.addToolBar("메인 툴바")
   self.main_toolbar.setObjectName("mainToolbar")  # 필수!
   ```
   - objectName 미설정 시 saveState() 경고 발생
   - 명명 규칙: camelCase 사용 (예: strategyDock, mainToolbar)

6. **백테스트 사용법**
   ```python
   from src.domain.backtest import BacktestEngine, BacktestConfig
   from decimal import Decimal
   from datetime import datetime
   
   config = BacktestConfig(
       start_date=datetime(2023, 1, 1),
       end_date=datetime(2023, 12, 31),
       initial_capital=Decimal("10000000"),
       commission_rate=Decimal("0.0015"),
       tax_rate=Decimal("0.003")
   )
   
   engine = BacktestEngine(config, strategy, data_provider, portfolio_manager)
   result = await engine.run()
   ```

## 🔄 다음 작업 단계

1. **진행 중**: Phase 8 - Trading UI 개발 (25%)
2. **다음**: Phase 9 - 전략 시스템 구현
3. **그 다음**: Phase 10 - 리스크 관리 시스템
4. **이후**: Phase 11 - 테스트 및 최적화

## 📈 주요 성과 지표

### 테스트 커버리지
- **KiwoomMarketDataProvider**: 70.59% (13개 테스트 통과)
- **MarketData 모델**: 88.36%
- **백테스트 엔진**: 완전 테스트 (60개 테스트 통과)
- **UI 컴포넌트**: 진행 중
- **전체 프로젝트**: ~60%

### 구현 완료 기능
- ✅ 인증 시스템 (OAuth2, 자격증명 관리)
- ✅ API 클라이언트 (Rate Limiting, 재시도, 캐싱)
- ✅ 데이터 수집 (현재가, 일봉, 정규화)
- ✅ 실시간 구독/해제 시스템
- ✅ 배치 요청 및 연속조회
- ✅ 백테스트 엔진 (이벤트 기반)
- ✅ 포트폴리오 관리 및 리스크 검증
- ✅ 성과 지표 계산 (Sharpe, VaR 등)
- ✅ 한국 시장 특화 거래 비용 모델
- 🔄 PyQt5 Trading UI (진행 중)

---

**마지막 업데이트**: 2025-07-13
**버전**: 0.1.0
**GitHub**: https://github.com/ParkKyunHo/K_STOCK_REST_API