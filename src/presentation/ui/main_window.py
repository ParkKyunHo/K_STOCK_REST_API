# -*- coding: utf-8 -*-
"""
메인 윈도우 구현
"""
import logging
import random
from typing import Optional

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QKeySequence, QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QMenu, QMenuBar, QToolBar,
    QStatusBar, QDockWidget, QTabWidget, QWidget,
    QVBoxLayout, QMessageBox, QTextEdit
)

# 위젯 imports
from .widgets.strategy_list import StrategyListWidget
from .widgets.backtest_config import BacktestConfigWidget
from .widgets.progress_widget import ProgressWidget
from .widgets.chart_widget import ChartWidget
from .widgets.performance_dashboard import PerformanceDashboard


class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """메인 윈도우 초기화"""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.current_file: Optional[str] = None
        self.is_modified = False
        
        # UI 초기화
        self._init_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._create_dock_widgets()
        self._create_central_widget()
        self._connect_signals()
        
        # 기본 설정
        self.setWindowTitle("K-Stock Trading System")
        self.resize(1280, 800)
        
    def _init_ui(self):
        """UI 기본 설정"""
        # 윈도우 플래그 설정
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        
        # 도킹 옵션
        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )
        
    def _create_actions(self):
        """액션 생성"""
        # 파일 메뉴 액션
        self.new_action = QAction("새 전략(&N)", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.setStatusTip("새 전략 생성")
        
        self.open_action = QAction("열기(&O)...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.setStatusTip("전략 파일 열기")
        
        self.save_action = QAction("저장(&S)", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.setStatusTip("현재 전략 저장")
        
        self.save_as_action = QAction("다른 이름으로 저장(&A)...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.setStatusTip("다른 이름으로 저장")
        
        self.exit_action = QAction("종료(&X)", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.setStatusTip("프로그램 종료")
        
        # 편집 메뉴 액션
        self.cut_action = QAction("잘라내기(&T)", self)
        self.cut_action.setShortcut(QKeySequence.Cut)
        
        self.copy_action = QAction("복사(&C)", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        
        self.paste_action = QAction("붙여넣기(&P)", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        
        # 보기 메뉴 액션
        self.toggle_strategy_dock_action = QAction("전략 목록(&S)", self)
        self.toggle_strategy_dock_action.setCheckable(True)
        self.toggle_strategy_dock_action.setChecked(True)
        
        self.toggle_log_dock_action = QAction("로그(&L)", self)
        self.toggle_log_dock_action.setCheckable(True)
        self.toggle_log_dock_action.setChecked(True)
        
        # 전략 메뉴 액션
        self.load_strategy_action = QAction("전략 불러오기(&L)...", self)
        self.reload_strategy_action = QAction("전략 새로고침(&R)", self)
        self.reload_strategy_action.setShortcut("F5")
        
        self.strategy_config_action = QAction("전략 설정(&C)...", self)
        
        # 백테스트 메뉴 액션
        self.run_backtest_action = QAction("백테스트 실행(&R)", self)
        self.run_backtest_action.setShortcut("F9")
        
        self.stop_backtest_action = QAction("백테스트 중지(&S)", self)
        self.stop_backtest_action.setShortcut("Shift+F9")
        self.stop_backtest_action.setEnabled(False)
        
        self.backtest_config_action = QAction("백테스트 설정(&C)...", self)
        
        # 도움말 메뉴 액션
        self.about_action = QAction("정보(&A)...", self)
        self.help_action = QAction("도움말(&H)", self)
        self.help_action.setShortcut("F1")
        
    def _create_menus(self):
        """메뉴 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        self.file_menu = menubar.addMenu("파일(&F)")
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)
        
        # 편집 메뉴
        self.edit_menu = menubar.addMenu("편집(&E)")
        self.edit_menu.addAction(self.cut_action)
        self.edit_menu.addAction(self.copy_action)
        self.edit_menu.addAction(self.paste_action)
        
        # 보기 메뉴
        self.view_menu = menubar.addMenu("보기(&V)")
        self.view_menu.addAction(self.toggle_strategy_dock_action)
        self.view_menu.addAction(self.toggle_log_dock_action)
        
        # 전략 메뉴
        self.strategy_menu = menubar.addMenu("전략(&S)")
        self.strategy_menu.addAction(self.load_strategy_action)
        self.strategy_menu.addAction(self.reload_strategy_action)
        self.strategy_menu.addSeparator()
        self.strategy_menu.addAction(self.strategy_config_action)
        
        # 백테스트 메뉴
        self.backtest_menu = menubar.addMenu("백테스트(&B)")
        self.backtest_menu.addAction(self.run_backtest_action)
        self.backtest_menu.addAction(self.stop_backtest_action)
        self.backtest_menu.addSeparator()
        self.backtest_menu.addAction(self.backtest_config_action)
        
        # 도움말 메뉴
        self.help_menu = menubar.addMenu("도움말(&H)")
        self.help_menu.addAction(self.help_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)
        
    def _create_toolbars(self):
        """툴바 생성"""
        # 메인 툴바
        self.main_toolbar = self.addToolBar("메인 툴바")
        self.main_toolbar.setObjectName("mainToolbar")
        self.main_toolbar.addAction(self.new_action)
        self.main_toolbar.addAction(self.open_action)
        self.main_toolbar.addAction(self.save_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.cut_action)
        self.main_toolbar.addAction(self.copy_action)
        self.main_toolbar.addAction(self.paste_action)
        
        # 전략 툴바
        self.strategy_toolbar = self.addToolBar("전략 툴바")
        self.strategy_toolbar.setObjectName("strategyToolbar")
        self.strategy_toolbar.addAction(self.load_strategy_action)
        self.strategy_toolbar.addAction(self.reload_strategy_action)
        self.strategy_toolbar.addAction(self.strategy_config_action)
        
        # 백테스트 툴바
        self.backtest_toolbar = self.addToolBar("백테스트 툴바")
        self.backtest_toolbar.setObjectName("backtestToolbar")
        self.backtest_toolbar.addAction(self.run_backtest_action)
        self.backtest_toolbar.addAction(self.stop_backtest_action)
        self.backtest_toolbar.addAction(self.backtest_config_action)
        
    def _create_status_bar(self):
        """상태바 생성"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("준비")
        
    def _create_dock_widgets(self):
        """도킹 위젯 생성"""
        # 전략 목록 도킹
        self.strategy_dock = QDockWidget("전략 목록", self)
        self.strategy_dock.setObjectName("strategyDock")
        self.strategy_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 전략 목록 위젯
        self.strategy_list_widget = StrategyListWidget()
        self.strategy_dock.setWidget(self.strategy_list_widget)
        
        # 시그널 연결
        self.strategy_list_widget.strategy_double_clicked.connect(self._on_strategy_double_clicked)
        self.strategy_list_widget.strategy_selected.connect(self._on_strategy_selected)
        
        self.addDockWidget(Qt.LeftDockWidgetArea, self.strategy_dock)
        
        # 로그 도킹
        self.log_dock = QDockWidget("로그", self)
        self.log_dock.setObjectName("logDock")
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        
        # 로그 텍스트 위젯
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_dock.setWidget(self.log_widget)
        
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        
        # 백테스트 설정 도킹
        self.backtest_config_dock = QDockWidget("백테스트 설정", self)
        self.backtest_config_dock.setObjectName("backtestConfigDock")
        self.backtest_config_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 백테스트 설정 위젯
        self.backtest_config_widget = BacktestConfigWidget()
        self.backtest_config_dock.setWidget(self.backtest_config_widget)
        
        # 시그널 연결
        self.backtest_config_widget.run_requested.connect(self._on_run_backtest)
        
        self.addDockWidget(Qt.RightDockWidgetArea, self.backtest_config_dock)
        
    def _create_central_widget(self):
        """중앙 위젯 생성"""
        # 탭 위젯 생성
        self.central_tabs = QTabWidget()
        self.central_tabs.setTabsClosable(True)
        self.central_tabs.setMovable(True)
        
        # 환영 탭 추가
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        welcome_text = QTextEdit()
        welcome_text.setReadOnly(True)
        welcome_text.setHtml("""
        <h1>K-Stock Trading System</h1>
        <p>한국 주식 자동매매 시스템에 오신 것을 환영합니다!</p>
        <h2>시작하기</h2>
        <ul>
            <li>새 전략을 만들려면: 파일 → 새 전략 (Ctrl+N)</li>
            <li>기존 전략을 열려면: 파일 → 열기 (Ctrl+O)</li>
            <li>백테스트를 실행하려면: 백테스트 → 백테스트 실행 (F9)</li>
        </ul>
        """)
        
        layout.addWidget(welcome_text)
        self.central_tabs.addTab(welcome_widget, "환영")
        
        # 중앙 위젯으로 설정
        self.setCentralWidget(self.central_tabs)
        
        # 진행률 위젯 (숨김 상태로 시작)
        self.progress_widget = ProgressWidget()
        self.progress_widget.pause_requested.connect(self._on_pause_backtest)
        self.progress_widget.resume_requested.connect(self._on_resume_backtest)
        self.progress_widget.stop_requested.connect(self._on_stop_backtest)
        self.progress_widget.hide()
        
    def _connect_signals(self):
        """시그널 연결"""
        # 파일 메뉴
        self.new_action.triggered.connect(self.on_new_strategy)
        self.open_action.triggered.connect(self.on_open_file)
        self.save_action.triggered.connect(self.on_save_file)
        self.save_as_action.triggered.connect(self.on_save_as_file)
        self.exit_action.triggered.connect(self.close)
        
        # 보기 메뉴
        self.toggle_strategy_dock_action.triggered.connect(self.toggle_strategy_dock)
        self.toggle_log_dock_action.triggered.connect(self.toggle_log_dock)
        
        # 도움말 메뉴
        self.about_action.triggered.connect(self.show_about_dialog)
        
        # 탭 닫기
        self.central_tabs.tabCloseRequested.connect(self.on_tab_close)
        
        # 백테스트 메뉴
        self.run_backtest_action.triggered.connect(self._on_run_backtest_action)
        self.stop_backtest_action.triggered.connect(self._on_stop_backtest)
        
    def show_status_message(self, message: str, timeout: int = 0):
        """상태바 메시지 표시"""
        self.status_bar.showMessage(message, timeout)
        
    def update_window_title(self, filepath: Optional[str] = None, modified: bool = False):
        """윈도우 제목 업데이트"""
        title = "K-Stock Trading System"
        
        if filepath:
            import os
            filename = os.path.basename(filepath)
            title = f"{filename} - {title}"
            
        if modified:
            title = f"*{title}"
            
        self.setWindowTitle(title)
        
    def toggle_strategy_dock(self):
        """전략 도킹 토글"""
        self.strategy_dock.setVisible(not self.strategy_dock.isVisible())
        
    def toggle_log_dock(self):
        """로그 도킹 토글"""
        self.log_dock.setVisible(not self.log_dock.isVisible())
        
    def on_new_strategy(self):
        """새 전략 생성"""
        self.logger.info("Creating new strategy")
        # TODO: 전략 생성 다이얼로그 구현
        
    def on_open_file(self):
        """파일 열기"""
        self.logger.info("Opening file")
        # TODO: 파일 열기 다이얼로그 구현
        
    def on_save_file(self):
        """파일 저장"""
        self.logger.info("Saving file")
        # TODO: 파일 저장 구현
        
    def on_save_as_file(self):
        """다른 이름으로 저장"""
        self.logger.info("Saving file as")
        # TODO: 다른 이름으로 저장 구현
        
    def on_tab_close(self, index: int):
        """탭 닫기"""
        # 환영 탭은 닫지 않음
        if index == 0 and self.central_tabs.tabText(0) == "환영":
            return
            
        self.central_tabs.removeTab(index)
        
    def show_about_dialog(self):
        """About 다이얼로그 표시"""
        QMessageBox.about(
            self,
            "K-Stock Trading System",
            """<h2>K-Stock Trading System</h2>
            <p>버전: v1.0.0</p>
            <p>한국 주식 자동매매 시스템</p>
            <p>© 2025 KStock. All rights reserved.</p>
            """
        )
        
    def add_log_message(self, message: str, level: str = "INFO"):
        """로그 메시지 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 레벨별 색상
        colors = {
            "DEBUG": "#808080",
            "INFO": "#FFFFFF",
            "WARNING": "#FFA500",
            "ERROR": "#FF0000",
            "CRITICAL": "#FF00FF"
        }
        
        color = colors.get(level, "#FFFFFF")
        html = f'<span style="color: {color}">[{timestamp}] [{level}] {message}</span>'
        
        self.log_widget.append(html)
        
    def _on_strategy_selected(self, strategy: dict):
        """전략 선택 시"""
        self.logger.info(f"Strategy selected: {strategy.get('name', 'Unknown')}")
        self.show_status_message(f"전략 선택됨: {strategy.get('name', 'Unknown')}")
        
    def _on_strategy_double_clicked(self, strategy: dict):
        """전략 더블클릭 시"""
        self.logger.info(f"Strategy double-clicked: {strategy.get('name', 'Unknown')}")
        # TODO: 전략 설정 다이얼로그 열기
        
    def load_sample_strategies(self):
        """샘플 전략 로드 (테스트용)"""
        sample_strategies = [
            {
                "id": "ma_crossover",
                "name": "이동평균 크로스오버",
                "version": "1.0.0",
                "description": "단기/장기 이동평균 교차 전략",
                "category": "추세추종",
                "author": "System"
            },
            {
                "id": "rsi_strategy",
                "name": "RSI 전략",
                "version": "1.1.0",
                "description": "RSI 과매수/과매도 전략",
                "category": "모멘텀",
                "author": "System"
            },
            {
                "id": "bollinger_bands",
                "name": "볼린저 밴드",
                "version": "0.9.0",
                "description": "볼린저 밴드 돌파 전략",
                "category": "변동성",
                "author": "System"
            }
        ]
        
        self.strategy_list_widget.load_strategies(sample_strategies)
        self.add_log_message("샘플 전략 로드 완료", "INFO")
        
    def closeEvent(self, event: QCloseEvent):
        """종료 이벤트"""
        # 수정된 내용이 있는지 확인
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "저장하지 않은 변경사항이 있습니다. 정말 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
                
        # 설정 저장
        settings = QSettings("KStock", "TradingSystem")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        event.accept()
        
    def _on_run_backtest_action(self):
        """백테스트 실행 액션"""
        # 백테스트 설정 가져오기
        config = self.backtest_config_widget.get_config()
        self._on_run_backtest(config)
        
    def _on_run_backtest(self, config: dict):
        """백테스트 실행"""
        self.logger.info("Starting backtest with config: %s", config)
        
        # 선택된 전략 확인
        selected_items = self.strategy_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "전략을 선택해주세요.")
            return
            
        # 진행률 위젯을 탭으로 추가
        if hasattr(self, '_progress_tab_index'):
            self.central_tabs.removeTab(self._progress_tab_index)
            
        self._progress_tab_index = self.central_tabs.addTab(
            self.progress_widget, 
            "백테스트 진행"
        )
        self.central_tabs.setCurrentIndex(self._progress_tab_index)
        
        # 진행률 위젯 시작
        self.progress_widget.show()
        self.progress_widget.start()
        
        # 버튼 상태 변경
        self.run_backtest_action.setEnabled(False)
        self.stop_backtest_action.setEnabled(True)
        
        # 상태 메시지
        self.show_status_message("백테스트 실행 중...")
        self.add_log_message("백테스트 시작", "INFO")
        
        # TODO: 실제 백테스트 엔진 연결
        # 임시로 진행률 시뮬레이션
        self._simulate_backtest_progress()
        
    def _simulate_backtest_progress(self):
        """백테스트 진행률 시뮬레이션 (테스트용)"""
        from PyQt5.QtCore import QTimer
        import random
        
        self._progress = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_simulated_progress)
        self._timer.start(100)  # 100ms마다 업데이트
        
    def _update_simulated_progress(self):
        """시뮬레이션 진행률 업데이트"""
        self._progress += random.uniform(0.5, 2.0)
        
        if self._progress >= 100:
            self._progress = 100
            self._timer.stop()
            self._on_backtest_completed()
            
        # 진행률 업데이트
        self.progress_widget.update_progress(
            self._progress / 100,
            f"처리 중... {self._progress:.1f}%"
        )
        
        # 추가 정보 업데이트
        self.progress_widget.update_trades(int(self._progress * 10))
        self.progress_widget.update_positions(random.randint(1, 10))
        self.progress_widget.update_performance(
            random.uniform(-5, 15),
            10000000 * (1 + self._progress / 100 * 0.1)
        )
        
    def _on_pause_backtest(self):
        """백테스트 일시정지"""
        self.logger.info("Pausing backtest")
        self.add_log_message("백테스트 일시정지", "WARNING")
        # TODO: 백테스트 엔진 일시정지
        
    def _on_resume_backtest(self):
        """백테스트 재개"""
        self.logger.info("Resuming backtest")
        self.add_log_message("백테스트 재개", "INFO")
        # TODO: 백테스트 엔진 재개
        
    def _on_stop_backtest(self):
        """백테스트 중지"""
        self.logger.info("Stopping backtest")
        
        reply = QMessageBox.question(
            self,
            "백테스트 중지",
            "백테스트를 중지하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if hasattr(self, '_timer'):
                self._timer.stop()
                
            self.progress_widget.stop()
            
            # 버튼 상태 복원
            self.run_backtest_action.setEnabled(True)
            self.stop_backtest_action.setEnabled(False)
            
            self.show_status_message("백테스트 중지됨")
            self.add_log_message("백테스트 중지됨", "WARNING")
            
    def _on_backtest_completed(self):
        """백테스트 완료"""
        self.progress_widget.stop()
        
        # 버튼 상태 복원
        self.run_backtest_action.setEnabled(True)
        self.stop_backtest_action.setEnabled(False)
        
        self.show_status_message("백테스트 완료")
        self.add_log_message("백테스트 완료", "INFO")
        
        # 결과 탭 추가
        self._add_result_tabs()
        
        QMessageBox.information(
            self,
            "백테스트 완료",
            "백테스트가 성공적으로 완료되었습니다."
        )
        
    def _add_result_tabs(self):
        """결과 탭 추가"""
        # 성과 대시보드 탭 (첫 번째)
        performance_dashboard = PerformanceDashboard()
        self.central_tabs.addTab(performance_dashboard, "성과 분석")
        
        # 샘플 성과 데이터로 업데이트
        self._update_sample_performance(performance_dashboard)
        
        # 차트 탭
        price_chart = ChartWidget("가격 차트")
        self.central_tabs.addTab(price_chart, "가격 차트")
        
        # 샘플 데이터로 차트 그리기
        self._plot_sample_chart(price_chart)
        
        # 자산 곡선 탭
        equity_chart = ChartWidget("자산 곡선")
        self.central_tabs.addTab(equity_chart, "자산 곡선")
        
        # 샘플 자산 곡선
        self._plot_sample_equity(equity_chart)
        
    def _plot_sample_chart(self, chart: ChartWidget):
        """샘플 차트 그리기"""
        from datetime import datetime, timedelta
        import random
        
        # 샘플 캔들 데이터 생성
        data = []
        base_price = 50000
        start_date = datetime.now() - timedelta(days=100)
        
        for i in range(100):
            date = start_date + timedelta(days=i)
            open_price = base_price + random.uniform(-1000, 1000)
            close_price = open_price + random.uniform(-500, 500)
            high_price = max(open_price, close_price) + random.uniform(0, 200)
            low_price = min(open_price, close_price) - random.uniform(0, 200)
            
            data.append((date, open_price, high_price, low_price, close_price))
            base_price = close_price
            
        chart.plot_candlestick(data)
        
    def _plot_sample_equity(self, chart: ChartWidget):
        """샘플 자산 곡선 그리기"""
        from datetime import datetime, timedelta
        import random
        
        # 샘플 자산 데이터 생성
        data = []
        equity = 10000000
        start_date = datetime.now() - timedelta(days=100)
        
        for i in range(100):
            date = start_date + timedelta(days=i)
            change = random.uniform(-0.02, 0.03)
            equity *= (1 + change)
            data.append((date, equity))
            
        chart.plot_line(data, "자산 가치", "#4CAF50")
        
    def _update_sample_performance(self, dashboard: PerformanceDashboard):
        """샘플 성과 데이터 업데이트"""
        from datetime import datetime, timedelta
        import random
        
        # 샘플 성과 데이터 생성
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        
        sample_data = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'period_days': 365,
            'initial_capital': 10000000,
            'final_capital': 11500000,
            'total_return': 15.0,
            'annual_return': 15.0,
            'sharpe_ratio': 1.85,
            'max_drawdown': -8.5,
            'win_rate': 65.2,
            'profit_factor': 1.42,
            'volatility': 0.18,  # 18%
            'beta': 0.95,
            'var_95': -0.035,  # -3.5%
            'var_99': -0.055,  # -5.5%
            'cvar_95': -0.045,  # -4.5%
            'total_trades': 156,
            'winning_trades': 102,
            'losing_trades': 54,
            'avg_return': 0.65,
            'max_win': 8.2,
            'max_loss': -4.1,
            'sortino_ratio': 2.1,
            'calmar_ratio': 1.76
        }
        
        # 성과 대시보드 업데이트
        dashboard.update_performance_data(sample_data)