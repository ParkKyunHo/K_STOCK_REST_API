# Trading UI 사용 가이드

## 1. 개요

이 문서는 Phase 8에서 개발 중인 PyQt5 기반 Trading UI의 사용법을 설명합니다. Trading UI는 전략 관리, 백테스트 실행, 결과 분석을 위한 통합 환경을 제공합니다.

## 2. UI 실행

### 2.1 기본 실행

```bash
# 가상환경 활성화
source venv/bin/activate  # Windows: venv\Scripts\activate

# UI 실행
python run_trading_ui.py

# 또는
python -m src.presentation.ui.application
```

### 2.2 테스트 모드 실행

```bash
# 샘플 데이터로 UI 테스트
python test_ui.py
```

### 2.3 헤드리스 모드 (CI/CD용)

```bash
# UI 없이 백그라운드 실행
QT_QPA_PLATFORM=offscreen python run_trading_ui.py
```

## 3. 주요 화면 구성

### 3.1 메인 윈도우

```
┌─────────────────────────────────────────────────────────────┐
│ File  Edit  View  Strategy  Backtest  Tools  Help           │ <- 메뉴바
├─────────────────────────────────────────────────────────────┤
│ [새로고침] [백테스트 실행] [중지] [설정]                      │ <- 툴바
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌────────────────────────────────────────┐ │
│ │전략 목록    │ │                                          │ │
│ │             │ │         중앙 작업 영역                   │ │
│ │- MA Cross   │ │    (차트, 결과 테이블 등)               │ │
│ │- RSI        │ │                                          │ │
│ │- Bollinger  │ │                                          │ │
│ └─────────────┘ └────────────────────────────────────────┘ │
│                                                              │
│ 준비됨 | 연결됨 | 메모리: 125MB | CPU: 5%                  │ <- 상태바
└─────────────────────────────────────────────────────────────┘
```

### 3.2 도킹 위젯

- **전략 목록 (왼쪽)**: 사용 가능한 전략 표시
- **백테스트 설정 (오른쪽)**: 백테스트 파라미터 설정
- **로그 패널 (하단)**: 실행 로그 표시

## 4. 전략 관리

### 4.1 전략 로드

1. 전략 목록 위젯에서 자동으로 플러그인 디렉토리 스캔
2. 사용 가능한 전략이 트리 형태로 표시
3. 각 전략의 버전, 설명, 파라미터 정보 표시

### 4.2 전략 선택 및 설정

```python
# 전략 더블클릭 시 설정 다이얼로그 표시
def on_strategy_double_click(strategy_item):
    dialog = StrategyConfigDialog(strategy_item.strategy)
    if dialog.exec_():
        params = dialog.get_parameters()
        # 전략 파라미터 업데이트
```

### 4.3 전략 파라미터 설정

파라미터 타입별 입력 위젯:
- **INT**: SpinBox
- **FLOAT**: DoubleSpinBox
- **STRING**: LineEdit
- **BOOL**: CheckBox
- **ENUM**: ComboBox

## 5. 백테스트 실행

### 5.1 백테스트 설정

```python
# 백테스트 설정 위젯에서 설정
config = {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "initial_capital": 10000000,
    "commission_rate": 0.0015,  # 0.15%
    "tax_rate": 0.003,          # 0.3%
    "slippage_rate": 0.001      # 0.1%
}
```

### 5.2 실행 및 진행률 추적

1. **백테스트 실행 버튼** 클릭
2. 진행률 바에서 실시간 진행 상황 확인
3. 중지 버튼으로 언제든 중단 가능

```python
# 진행률 업데이트
engine.progress_updated.connect(
    lambda progress: progress_bar.setValue(int(progress * 100))
)
```

### 5.3 결과 분석

백테스트 완료 후 자동으로 표시되는 항목:
- 성과 지표 테이블
- 자산 곡선 차트
- 낙폭 차트
- 거래 내역 테이블

## 6. 차트 시스템

### 6.1 가격 차트

```python
# pyqtgraph를 사용한 고성능 차트
price_chart = PriceChartWidget()
price_chart.plot_candlestick(ohlcv_data)
price_chart.add_indicator("MA20", ma20_data)
price_chart.add_volume_bars(volume_data)
```

### 6.2 자산 곡선

```python
# 포트폴리오 가치 변화 표시
equity_chart = EquityCurveWidget()
equity_chart.plot_equity_curve(portfolio_values)
equity_chart.plot_benchmark(benchmark_values)
equity_chart.highlight_drawdowns()
```

## 7. 성과 분석 도구

### 7.1 성과 지표 테이블

| 지표 | 값 | 설명 |
|------|-----|------|
| 총 수익률 | 15.3% | 전체 기간 수익률 |
| 연환산 수익률 | 12.1% | 연간 기준 환산 |
| 샤프 비율 | 1.85 | 위험 조정 수익률 |
| 최대 낙폭 | -8.5% | 최대 손실폭 |
| 승률 | 65.2% | 수익 거래 비율 |

### 7.2 거래 분석

```python
# 거래 내역 테이블
trade_table = TradeAnalysisWidget()
trade_table.load_trades(backtest_result.trades)
trade_table.show_statistics()
```

## 8. 실시간 거래 (향후 기능)

### 8.1 실시간 모드 전환

```python
# 실시간/백테스트 모드 전환
if mode_switch.isChecked():
    app.set_mode(TradingMode.LIVE)
else:
    app.set_mode(TradingMode.BACKTEST)
```

### 8.2 실시간 데이터 표시

- 실시간 호가창
- 체결 내역
- 포지션 모니터링
- 손익 추적

## 9. 설정 및 사용자 정의

### 9.1 테마 설정

```python
# 다크 테마 (기본)
app.setStyleSheet(qdarkstyle.load_stylesheet())

# 라이트 테마로 변경
app.setStyleSheet("")
```

### 9.2 레이아웃 저장/복원

```python
# 현재 레이아웃 저장
settings = QSettings("KStock", "TradingUI")
settings.setValue("geometry", self.saveGeometry())
settings.setValue("windowState", self.saveState())

# 레이아웃 복원
self.restoreGeometry(settings.value("geometry"))
self.restoreState(settings.value("windowState"))
```

## 10. 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| Ctrl+R | 백테스트 실행 |
| Ctrl+S | 중지 |
| F5 | 새로고침 |
| Ctrl+O | 전략 열기 |
| Ctrl+Q | 종료 |
| F1 | 도움말 |

## 11. 문제 해결

### 11.1 UI가 표시되지 않음

```bash
# Qt 플랫폼 플러그인 오류 시
export QT_QPA_PLATFORM=xcb  # Linux
set QT_QPA_PLATFORM=windows  # Windows
```

### 11.2 폰트 렌더링 문제

```python
# 폰트 설정 변경
font = QFont("맑은 고딕", 10)
app.setFont(font)
```

### 11.3 차트 성능 문제

```python
# 다운샘플링 활성화
chart.setDownsampling(auto=True, mode='peak')

# 안티앨리어싱 비활성화
chart.setAntialiasing(False)
```

### 11.4 Qt objectName 경고

**문제**: "QMainWindow::saveState(): objectName not set for QDockWidget" 경고 발생

**해결방법**:
```python
# ❌ 잘못된 코드
self.strategy_dock = QDockWidget("전략 목록", self)

# ✅ 올바른 코드
self.strategy_dock = QDockWidget("전략 목록", self)
self.strategy_dock.setObjectName("strategyDock")  # 필수!
```

모든 QDockWidget과 QToolBar에는 반드시 objectName을 설정해야 합니다. 이는 Qt가 윈도우 상태를 저장/복원할 때 필요합니다.

### 11.5 한글 폰트 렌더링 문제

**문제**: WSL2 또는 Linux 환경에서 한글이 깨짐

**해결방법**:
```python
# 시스템별 폰트 설정
from PyQt5.QtGui import QFont
import sys

font = QFont()
if sys.platform == "win32":
    font.setFamily("맑은 고딕")
elif sys.platform == "linux":
    font.setFamily("Noto Sans CJK KR")
elif sys.platform == "darwin":
    font.setFamily("Apple SD Gothic Neo")
font.setPointSize(10)
app.setFont(font)

# 파일 상단에 UTF-8 인코딩 명시
# -*- coding: utf-8 -*-
```

**폰트 설치** (Linux):
```bash
sudo apt-get install fonts-noto-cjk fonts-nanum
```

### 11.6 WSL2 GUI 표시 문제

**문제**: "could not load the Qt platform plugin "xcb"" 오류

**해결방법**:
1. X11 서버 설치 및 설정
   ```bash
   ./setup_x11_wsl2.sh
   ```

2. VcXsrv 실행 (Windows)
   - `C:\Users\[사용자명]\Documents\vcxsrv.xlaunch` 파일 실행
   - "Disable access control" 옵션 체크 필수

3. 환경변수 설정 (여러 방법 중 선택)
   ```bash
   # 방법 1: 기본 게이트웨이 IP 사용 (권장)
   export DISPLAY=$(ip route show | grep -i default | awk '{ print $3 }'):0
   
   # 방법 2: resolv.conf 사용
   export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
   
   # 방법 3: 직접 IP 설정 (Windows에서 ipconfig로 확인한 IP)
   export DISPLAY=172.27.112.1:0  # 예시
   ```

4. 영구 설정 (.bashrc에 추가)
   ```bash
   echo 'export DISPLAY=$(ip route show | grep -i default | awk "{ print $3 }"):0' >> ~/.bashrc
   source ~/.bashrc
   ```

## 12. 개발자 가이드

### 12.1 PyQt5 코딩 표준

**필수 규칙**:
1. **objectName 설정 (중요!)**
   ```python
   # 모든 QDockWidget과 QToolBar에 필수
   self.dock = QDockWidget("제목", self)
   self.dock.setObjectName("myDock")  # 필수!
   
   self.toolbar = self.addToolBar("도구")
   self.toolbar.setObjectName("myToolbar")  # 필수!
   ```

2. **한글 인코딩**
   ```python
   # -*- coding: utf-8 -*-  # 파일 상단에 필수
   ```

3. **시그널/슬롯 명명 규칙**
   ```python
   # 시그널: 동사_과거분사
   data_loaded = pyqtSignal(dict)
   item_selected = pyqtSignal(str)
   
   # 슬롯: on_ 접두사
   def on_button_clicked(self):
       pass
   ```

4. **위젯 import는 모듈 레벨에서**
   ```python
   # ❌ 잘못된 예: 메서드 내부 import
   def create_widget(self):
       from .widgets.my_widget import MyWidget  # 잘못됨!
   
   # ✅ 올바른 예: 모듈 레벨 import
   from .widgets.my_widget import MyWidget
   
   def create_widget(self):
       widget = MyWidget()
   ```

### 12.2 새로운 위젯 추가

```python
class MyCustomWidget(QWidget):
    """커스텀 위젯 예제"""
    
    # 시그널 정의
    data_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("myCustomWidget")  # objectName 설정 필수!
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        # UI 구성
        self.setLayout(layout)
    
    def _connect_signals(self):
        """시그널 연결"""
        pass
```

### 12.3 테스트 작성

```python
@pytest.fixture
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_custom_widget(qapp):
    """위젯 테스트"""
    widget = MyCustomWidget()
    widget.show()
    
    # 테스트 로직
    assert widget.isVisible()
```

### 12.4 비동기 작업 처리

```python
class AsyncWorker(QThread):
    """백그라운드 작업 처리"""
    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    
    def __init__(self, task_function):
        super().__init__()
        self.task_function = task_function
    
    def run(self):
        try:
            result = self.task_function(
                progress_callback=self.progress.emit
            )
            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

## 13. 성능 최적화

### 13.1 대용량 데이터 처리

```python
# 가상화된 테이블 사용
class VirtualTableModel(QAbstractTableModel):
    """대용량 데이터용 가상 테이블 모델"""
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def data(self, index, role=Qt.DisplayRole):
        # 필요한 데이터만 로드
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]
```

### 13.2 메모리 관리

```python
# 주기적인 가비지 컬렉션
def cleanup_memory():
    import gc
    gc.collect()
    QApplication.processEvents()

# 타이머로 주기적 실행
timer = QTimer()
timer.timeout.connect(cleanup_memory)
timer.start(60000)  # 1분마다
```

## 14. 플러그인 시스템

### 14.1 UI 플러그인 인터페이스

```python
class IUIPlugin(ABC):
    """UI 플러그인 인터페이스"""
    
    @abstractmethod
    def get_widget(self) -> QWidget:
        """플러그인 위젯 반환"""
        pass
    
    @abstractmethod
    def get_menu_items(self) -> List[QAction]:
        """메뉴 항목 반환"""
        pass
```

### 14.2 플러그인 로드

```python
# 플러그인 디렉토리에서 자동 로드
plugin_loader = PluginLoader("plugins/ui")
plugins = plugin_loader.load_all()

for plugin in plugins:
    widget = plugin.get_widget()
    self.add_dock_widget(widget, plugin.name)
```

---

**작성일**: 2025-07-13  
**버전**: 1.0.0