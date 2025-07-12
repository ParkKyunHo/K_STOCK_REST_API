# Phase 10 리스크 관리 시스템 개발 이슈 기록

## 📅 작업 날짜: 2025-07-12

## 🎯 Phase 10 목표
- 포지션 크기 관리 시스템
- 손절/익절 로직 구현
- 최대 낙폭 제한 시스템
- VaR (Value at Risk) 계산 모듈
- 포트폴리오 리밸런싱 알고리즘

## ✅ 완료된 작업

### 1. 기존 시스템 분석
- **IRiskManager 인터페이스**: 완전히 정의되어 있음 ✅
- **PerformanceCalculator**: VaR 95%, 99% 계산 기능 포함 ✅
- **PortfolioManager**: 기본 리스크 검증 기능 포함 ✅
- **BacktestEngine**: 이벤트 기반 백테스트 프레임워크 ✅

### 2. 포지션 크기 관리 모듈 설계
- **PositionSizer 클래스**: 완전 설계 완료
- **포지션 크기 계산 방법**:
  - 고정 금액 방식 (FIXED_AMOUNT)
  - 포트폴리오 비율 방식 (PERCENTAGE)  
  - 리스크 기반 방식 (RISK_BASED)
  - 변동성 기반 방식 (VOLATILITY_BASED)
  - 켈리 기준 방식 (KELLY_CRITERION)
  - 동일 비중 방식 (EQUAL_WEIGHT)
- **RiskLimits 설정**:
  - 최대 포지션 비중: 20%
  - 최대 총 노출도: 90%
  - 거래당 리스크: 2%
  - 최소 현금 버퍼: 10%
  - 상관관계 최대 노출도: 40%

### 3. 손절/익절 관리 모듈 설계
- **StopLossManager 클래스**: 완전 설계 완료
- **손절 주문 유형**:
  - 고정 손절 (STOP_LOSS)
  - 익절 주문 (TAKE_PROFIT)
  - 트레일링 스톱 (TRAILING_STOP)
- **StopLossConfig 설정**:
  - 기본 손절 비율: 5%
  - 기본 수익비율: 2:1 (리스크:리워드)
  - 트레일링 스톱 임계값: 10% 수익 시 시작

## ❌ 발생한 문제점

### 1. 파일 인코딩 문제 ⚠️
**문제**: Python 파일에서 "source code string cannot contain null bytes" 오류 발생

**영향받은 파일들**:
- `src/domain/risk/position_sizer.py`
- `src/domain/risk/stop_loss_manager.py`

**증상**:
```bash
SyntaxError: source code string cannot contain null bytes
```

**원인 분석**:
- MultiEdit 도구 사용 시 한글 주석으로 인한 인코딩 문제 추정
- cat 명령어로 생성한 파일도 EOF 처리 문제 발생

**시도한 해결 방법**:
1. MultiEdit으로 파일 재생성 → 실패
2. cat << 'EOF' 방식으로 재생성 → 실패  
3. 간단한 영어 버전으로 재작성 → 여전히 null bytes 오류

**해결 필요사항**:
- 파일을 완전히 삭제 후 Write 도구로 재생성
- 한글 주석 사용 시 주의
- UTF-8 인코딩 명시적 확인

### 2. 테스트 환경 문제 ⚠️
**문제**: pytest 실행 시 모듈 import 오류

**오류 메시지**:
```bash
ModuleNotFoundError: No module named 'pytest_asyncio'
```

**영향**:
- 정규 pytest 테스트 실행 불가
- conftest.py 로드 실패

**우회 방법**:
- 간단한 독립 테스트 파일 작성 시도
- 하지만 파일 인코딩 문제로 인해 테스트 불가

### 3. Git 동기화 미완료 ⚠️
**문제**: 최근 커밋들이 원격 저장소에 푸시되지 않음

**현재 상태**:
- 로컬 최신 커밋: dcaa843 (Phase 9 완료)
- 원격 저장소 동기화 상태 불명
- Phase 10 관련 파일들 커밋 대기 상태

**미커밋 파일들**:
```
modified:   src/domain/risk/__init__.py
untracked:  src/domain/risk/position_sizer.py
untracked:  src/domain/risk/stop_loss_manager.py
untracked:  tests/unit/domain/risk/
untracked:  test_simple_position_sizer.py
untracked:  test_stop_loss_manager.py
```

## 🔄 내일 해결할 작업 계획

### 1. 파일 인코딩 문제 해결 (최우선)
- 문제 파일들 완전 삭제
- Write 도구로 단계적 재생성
- 영어 주석으로 먼저 작성 후 한글 추가
- import 테스트 통과 확인

### 2. Git 동기화 완료
- 현재 상태 백업
- 정상 파일들 먼저 커밋
- 자동 푸시 설정 구성
- 원격 저장소 동기화 확인

### 3. 테스트 환경 정비
- pytest-asyncio 의존성 해결
- 또는 별도 테스트 방식 구성
- 모든 모듈 import 검증

### 4. Phase 10 구현 완료
- 수정된 파일들로 완전한 기능 구현
- 통합 테스트 실행
- 문서화 완료

## 📝 교훈 및 개선사항

1. **인코딩 문제 예방**:
   - 한글 주석 사용 시 신중하게 접근
   - 파일 생성 후 즉시 import 테스트 실행
   - UTF-8 인코딩 명시적 확인

2. **Git 워크플로우 개선**:
   - 커밋 후 자동 푸시 설정 필요
   - 정기적인 원격 동기화 확인

3. **테스트 환경 안정화**:
   - 의존성 문제 사전 해결
   - 대안 테스트 방법 준비

## 📊 진행률
- **전체 Phase 10 진행률**: 30% (설계 완료, 구현 대기)
- **예상 완료일**: 2025-07-13 (내일)
- **주요 블로커**: 파일 인코딩 문제