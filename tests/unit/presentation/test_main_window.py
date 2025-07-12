# -*- coding: utf-8 -*-
"""
메인 윈도우 테스트
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QToolBar, 
    QStatusBar, QDockWidget, QTabWidget
)

from src.presentation.ui.main_window import MainWindow


@pytest.fixture
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestMainWindow:
    """메인 윈도우 테스트"""
    
    def test_window_initialization(self, qapp):
        """윈도우 초기화 테스트"""
        window = MainWindow()
        
        # 기본 속성 확인
        assert isinstance(window, QMainWindow)
        assert window.windowTitle() == "K-Stock Trading System"
        
        # 크기 확인
        assert window.width() >= 1280
        assert window.height() >= 800
        
    def test_create_menus(self, qapp):
        """메뉴 생성 테스트"""
        window = MainWindow()
        
        # 메뉴바 확인
        menubar = window.menuBar()
        assert isinstance(menubar, QMenuBar)
        
        # 파일 메뉴 확인
        file_menu = window.file_menu
        assert file_menu is not None
        assert file_menu.title() == "파일(&F)"
        
        # 편집 메뉴 확인
        edit_menu = window.edit_menu
        assert edit_menu is not None
        assert edit_menu.title() == "편집(&E)"
        
        # 보기 메뉴 확인
        view_menu = window.view_menu
        assert view_menu is not None
        assert view_menu.title() == "보기(&V)"
        
        # 전략 메뉴 확인
        strategy_menu = window.strategy_menu
        assert strategy_menu is not None
        assert strategy_menu.title() == "전략(&S)"
        
        # 백테스트 메뉴 확인
        backtest_menu = window.backtest_menu
        assert backtest_menu is not None
        assert backtest_menu.title() == "백테스트(&B)"
        
        # 도움말 메뉴 확인
        help_menu = window.help_menu
        assert help_menu is not None
        assert help_menu.title() == "도움말(&H)"
        
    def test_create_toolbars(self, qapp):
        """툴바 생성 테스트"""
        window = MainWindow()
        
        # 메인 툴바 확인
        main_toolbar = window.main_toolbar
        assert isinstance(main_toolbar, QToolBar)
        assert main_toolbar.windowTitle() == "메인 툴바"
        
        # 전략 툴바 확인
        strategy_toolbar = window.strategy_toolbar
        assert isinstance(strategy_toolbar, QToolBar)
        assert strategy_toolbar.windowTitle() == "전략 툴바"
        
        # 백테스트 툴바 확인
        backtest_toolbar = window.backtest_toolbar
        assert isinstance(backtest_toolbar, QToolBar)
        assert backtest_toolbar.windowTitle() == "백테스트 툴바"
        
    def test_create_status_bar(self, qapp):
        """상태바 생성 테스트"""
        window = MainWindow()
        
        # 상태바 확인
        statusbar = window.statusBar()
        assert isinstance(statusbar, QStatusBar)
        
        # 상태 메시지 테스트
        window.show_status_message("테스트 메시지")
        assert statusbar.currentMessage() == "테스트 메시지"
        
    def test_create_dock_widgets(self, qapp):
        """도킹 위젯 생성 테스트"""
        window = MainWindow()
        
        # 전략 목록 도킹 확인
        strategy_dock = window.strategy_dock
        assert isinstance(strategy_dock, QDockWidget)
        assert strategy_dock.windowTitle() == "전략 목록"
        assert strategy_dock.isVisible()
        
        # 로그 도킹 확인
        log_dock = window.log_dock
        assert isinstance(log_dock, QDockWidget)
        assert log_dock.windowTitle() == "로그"
        assert log_dock.isVisible()
        
    def test_create_central_widget(self, qapp):
        """중앙 위젯 생성 테스트"""
        window = MainWindow()
        
        # 중앙 위젯 확인
        central_widget = window.centralWidget()
        assert central_widget is not None
        
        # 탭 위젯 확인
        tab_widget = window.central_tabs
        assert isinstance(tab_widget, QTabWidget)
        assert tab_widget.count() >= 1
        
    def test_menu_actions(self, qapp):
        """메뉴 액션 테스트"""
        window = MainWindow()
        
        # 파일 메뉴 액션
        assert window.new_action is not None
        assert window.new_action.text() == "새 전략(&N)"
        assert window.new_action.shortcut().toString() == "Ctrl+N"
        
        assert window.open_action is not None
        assert window.open_action.text() == "열기(&O)..."
        assert window.open_action.shortcut().toString() == "Ctrl+O"
        
        assert window.save_action is not None
        assert window.save_action.text() == "저장(&S)"
        assert window.save_action.shortcut().toString() == "Ctrl+S"
        
        assert window.exit_action is not None
        assert window.exit_action.text() == "종료(&X)"
        
    def test_action_connections(self, qapp):
        """액션 연결 테스트"""
        window = MainWindow()
        
        # Mock 핸들러
        window.on_new_strategy = MagicMock()
        window.on_open_file = MagicMock()
        window.on_save_file = MagicMock()
        
        # 액션 트리거
        window.new_action.trigger()
        window.on_new_strategy.assert_called_once()
        
        window.open_action.trigger()
        window.on_open_file.assert_called_once()
        
        window.save_action.trigger()
        window.on_save_file.assert_called_once()
        
    def test_close_event(self, qapp):
        """종료 이벤트 테스트"""
        window = MainWindow()
        
        # 종료 확인 다이얼로그 모킹
        with patch('PyQt5.QtWidgets.QMessageBox.question') as mock_question:
            # 종료 확인
            mock_question.return_value = True
            
            # 종료 이벤트 시뮬레이션
            from PyQt5.QtGui import QCloseEvent
            event = QCloseEvent()
            window.closeEvent(event)
            
            # 다이얼로그 표시 확인
            mock_question.assert_called_once()
            
    def test_show_about_dialog(self, qapp):
        """About 다이얼로그 테스트"""
        window = MainWindow()
        
        # About 다이얼로그 모킹
        with patch('PyQt5.QtWidgets.QMessageBox.about') as mock_about:
            window.show_about_dialog()
            
            # 다이얼로그 표시 확인
            mock_about.assert_called_once()
            args = mock_about.call_args[0]
            assert "K-Stock Trading System" in args[1]
            assert "v1.0.0" in args[2]
            
    def test_toggle_dock_visibility(self, qapp):
        """도킹 위젯 표시/숨김 테스트"""
        window = MainWindow()
        
        # 전략 도킹 숨기기
        window.strategy_dock.setVisible(False)
        assert not window.strategy_dock.isVisible()
        
        # 전략 도킹 표시
        window.toggle_strategy_dock()
        assert window.strategy_dock.isVisible()
        
        # 다시 숨기기
        window.toggle_strategy_dock()
        assert not window.strategy_dock.isVisible()
        
    def test_update_window_title(self, qapp):
        """윈도우 제목 업데이트 테스트"""
        window = MainWindow()
        
        # 파일 경로 설정
        window.update_window_title("/path/to/strategy.py")
        assert "strategy.py" in window.windowTitle()
        assert "K-Stock Trading System" in window.windowTitle()
        
        # 수정 표시
        window.update_window_title("/path/to/strategy.py", modified=True)
        assert "*" in window.windowTitle()
        
    def test_toolbar_actions(self, qapp):
        """툴바 액션 테스트"""
        window = MainWindow()
        
        # 메인 툴바 액션 확인
        main_actions = window.main_toolbar.actions()
        assert len(main_actions) > 0
        
        # 전략 툴바 액션 확인
        strategy_actions = window.strategy_toolbar.actions()
        assert len(strategy_actions) > 0
        
        # 백테스트 툴바 액션 확인
        backtest_actions = window.backtest_toolbar.actions()
        assert len(backtest_actions) > 0