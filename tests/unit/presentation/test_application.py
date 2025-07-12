# -*- coding: utf-8 -*-
"""
Trading UI 어플리케이션 테스트
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow

from src.presentation.ui.application import TradingApplication


@pytest.fixture
def qapp():
    """QApplication fixture"""
    # QApplication이 이미 존재하는지 확인
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # 테스트 후 정리는 pytest-qt가 자동으로 처리


class TestTradingApplication:
    """Trading 어플리케이션 테스트"""
    
    def test_application_initialization(self, qapp):
        """어플리케이션 초기화 테스트"""
        app = TradingApplication()
        
        # 기본 속성 확인
        assert app.name == "K-Stock Trading System"
        assert app.version == "1.0.0"
        assert app.main_window is None
        
    def test_create_main_window(self, qapp):
        """메인 윈도우 생성 테스트"""
        app = TradingApplication()
        
        # 메인 윈도우 생성
        window = app.create_main_window()
        
        # 윈도우 속성 확인
        assert isinstance(window, QMainWindow)
        assert window.windowTitle() == "K-Stock Trading System v1.0.0"
        assert window.minimumWidth() >= 1024
        assert window.minimumHeight() >= 768
        
        # 메인 윈도우 저장 확인
        assert app.main_window == window
        
    def test_setup_theme(self, qapp):
        """테마 설정 테스트"""
        app = TradingApplication()
        
        # 테마 설정
        app.setup_theme()
        
        # 스타일시트 적용 확인
        stylesheet = qapp.styleSheet()
        assert len(stylesheet) > 0
        
        # 다크 테마 요소 확인
        assert "background-color" in stylesheet
        assert "color" in stylesheet
        
    def test_setup_exception_handler(self, qapp):
        """예외 처리기 설정 테스트"""
        app = TradingApplication()
        
        # 예외 처리기 설정
        app.setup_exception_handler()
        
        # excepthook이 변경되었는지 확인
        assert sys.excepthook != sys.__excepthook__
        
        # 예외 처리기가 제대로 작동하는지 테스트
        with patch.object(app.logger, 'critical') as mock_log:
            try:
                raise ValueError("Test exception")
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                sys.excepthook(exc_type, exc_value, exc_tb)
                
            # 로그가 기록되었는지 확인
            mock_log.assert_called_once()
            
    def test_run_application(self, qapp):
        """어플리케이션 실행 테스트"""
        app = TradingApplication()
        
        # QApplication.exec_ 모킹
        with patch.object(QApplication, 'exec_', return_value=0) as mock_exec:
            result = app.run()
            
            # 실행 확인
            assert result == 0
            mock_exec.assert_called_once()
            
            # 메인 윈도우 생성 및 표시 확인
            assert app.main_window is not None
            assert app.main_window.isVisible()
            
    def test_cleanup_on_exit(self, qapp):
        """종료 시 정리 테스트"""
        app = TradingApplication()
        
        # 리소스 생성
        app.create_main_window()
        mock_resource = MagicMock()
        app._resources = {'test': mock_resource}
        
        # 정리
        app.cleanup()
        
        # 리소스 정리 확인
        mock_resource.close.assert_called_once()
        assert len(app._resources) == 0
        
    def test_load_configuration(self, qapp):
        """설정 로드 테스트"""
        app = TradingApplication()
        
        # 설정 로드
        config = app.load_configuration()
        
        # 설정 확인
        assert config['ui']['theme'] == 'dark'
        assert config['ui']['language'] == 'ko'
        assert config['ui']['window']['width'] == 1280
            
    def test_save_window_state(self, qapp):
        """윈도우 상태 저장 테스트"""
        app = TradingApplication()
        window = app.create_main_window()
        
        # 윈도우 크기 변경
        window.resize(1280, 800)
        window.move(100, 100)
        
        # 상태 저장
        with patch('src.presentation.ui.application.QSettings') as mock_settings:
            app.save_window_state()
            
            # 설정 저장 호출 확인
            mock_settings.return_value.setValue.assert_called()
            
    def test_restore_window_state(self, qapp):
        """윈도우 상태 복원 테스트"""
        app = TradingApplication()
        window = app.create_main_window()
        
        # 상태 복원
        with patch('src.presentation.ui.application.QSettings') as mock_settings:
            # 저장된 상태 시뮬레이션
            mock_settings.return_value.value.side_effect = [
                b'saved_geometry',  # geometry
                b'saved_state'      # state
            ]
            
            app.restore_window_state()
            
            # 복원 메서드 호출 확인
            assert mock_settings.return_value.value.call_count == 2
            
    def test_handle_fatal_error(self, qapp):
        """치명적 오류 처리 테스트"""
        app = TradingApplication()
        
        # 에러 다이얼로그 모킹
        with patch('PyQt5.QtWidgets.QMessageBox.critical') as mock_critical:
            app.handle_fatal_error("Test Error", "This is a test error")
            
            # 에러 다이얼로그 표시 확인
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Test Error" in args[1]
            assert "This is a test error" in args[2]
            
    def test_check_dependencies(self, qapp):
        """의존성 확인 테스트"""
        app = TradingApplication()
        
        # 의존성 확인
        result = app.check_dependencies()
        
        # 필수 모듈 확인
        assert result['PyQt5'] is True
        assert result['pyqtgraph'] is True
        assert result['pandas'] is True
        assert result['numpy'] is True