# -*- coding: utf-8 -*-
"""
Trading UI 메인 어플리케이션
"""
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QMessageBox

# from src.core.config import load_config  # TODO: Implement config loading
from .main_window import MainWindow


class TradingApplication:
    """Trading 시스템 메인 어플리케이션"""
    
    def __init__(self):
        """어플리케이션 초기화"""
        self.name = "K-Stock Trading System"
        self.version = "1.0.0"
        self.main_window: Optional[MainWindow] = None
        self._resources: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # 설정 저장소
        self.settings = QSettings("KStock", "TradingSystem")
        
    def create_main_window(self) -> MainWindow:
        """메인 윈도우 생성"""
        if self.main_window is None:
            self.main_window = MainWindow()
            self.main_window.setWindowTitle(f"{self.name} v{self.version}")
            self.main_window.setMinimumSize(1024, 768)
            
            # 윈도우 상태 복원
            self.restore_window_state()
            
        return self.main_window
        
    def setup_theme(self):
        """어플리케이션 테마 설정"""
        app = QApplication.instance()
        
        # 다크 테마 스타일시트
        dark_stylesheet = """
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: "DejaVu Sans", "Liberation Sans", "Noto Sans", sans-serif;
            font-size: 14px;
        }
        
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QMenuBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #3d3d3d;
        }
        
        QMenuBar::item:selected {
            background-color: #3d3d3d;
        }
        
        QMenu {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
        }
        
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
        
        QToolBar {
            background-color: #2d2d2d;
            border: none;
            spacing: 3px;
        }
        
        QPushButton {
            background-color: #3d3d3d;
            border: 1px solid #4d4d4d;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        
        QPushButton:pressed {
            background-color: #2d2d2d;
        }
        
        QTableWidget {
            background-color: #2d2d2d;
            gridline-color: #3d3d3d;
            border: 1px solid #3d3d3d;
        }
        
        QHeaderView::section {
            background-color: #3d3d3d;
            padding: 4px;
            border: none;
            border-right: 1px solid #4d4d4d;
            border-bottom: 1px solid #4d4d4d;
        }
        
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            background-color: #2d2d2d;
        }
        
        QTabBar::tab {
            background-color: #3d3d3d;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #2d2d2d;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border: none;
        }
        
        QScrollBar::handle:vertical {
            background-color: #4d4d4d;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #5d5d5d;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            padding: 4px;
            border-radius: 4px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #5d5d5d;
        }
        
        QComboBox {
            background-color: #3d3d3d;
            border: 1px solid #4d4d4d;
            padding: 4px;
            border-radius: 4px;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #ffffff;
            width: 0;
            height: 0;
        }
        
        QGroupBox {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            background-color: #1e1e1e;
        }
        
        QStatusBar {
            background-color: #2d2d2d;
            border-top: 1px solid #3d3d3d;
        }
        
        /* 차트 관련 스타일 */
        QGraphicsView {
            background-color: #1e1e1e;
            border: 1px solid #3d3d3d;
        }
        """
        
        app.setStyleSheet(dark_stylesheet)
        
        # 폰트 설정
        font = QFont()
        if sys.platform == "win32":
            font.setFamily("맑은 고딕")
        elif sys.platform == "linux":
            # Linux용 한글 폰트 설정
            font.setFamily("Noto Sans CJK KR")
        elif sys.platform == "darwin":
            font.setFamily("Apple SD Gothic Neo")
        else:
            # 기본 폰트
            font.setFamily("DejaVu Sans")
        font.setPointSize(10)
        app.setFont(font)
        
    def setup_exception_handler(self):
        """전역 예외 처리기 설정"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            """예외 처리"""
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            # 로깅
            self.logger.critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
            # 에러 메시지 생성
            error_msg = f"{exc_type.__name__}: {exc_value}"
            tb_str = ''.join(traceback.format_tb(exc_traceback))
            
            # 사용자에게 에러 표시
            if self.main_window:
                QMessageBox.critical(
                    self.main_window,
                    "예기치 않은 오류",
                    f"프로그램 실행 중 오류가 발생했습니다.\n\n{error_msg}\n\n상세 정보:\n{tb_str}"
                )
            
        sys.excepthook = handle_exception
        
    def load_configuration(self) -> Dict[str, Any]:
        """설정 로드"""
        try:
            # TODO: Implement actual config loading
            # config = load_config()
            # return config
            return {
                'ui': {
                    'theme': 'dark',
                    'language': 'ko',
                    'window': {
                        'width': 1280,
                        'height': 800
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            return {
                'ui': {
                    'theme': 'dark',
                    'language': 'ko',
                    'window': {
                        'width': 1280,
                        'height': 800
                    }
                }
            }
            
    def save_window_state(self):
        """윈도우 상태 저장"""
        if self.main_window:
            self.settings.setValue("geometry", self.main_window.saveGeometry())
            self.settings.setValue("windowState", self.main_window.saveState())
            
    def restore_window_state(self):
        """윈도우 상태 복원"""
        if self.main_window:
            geometry = self.settings.value("geometry")
            if geometry:
                self.main_window.restoreGeometry(geometry)
                
            state = self.settings.value("windowState")
            if state:
                self.main_window.restoreState(state)
                
    def handle_fatal_error(self, title: str, message: str):
        """치명적 오류 처리"""
        self.logger.critical(f"{title}: {message}")
        
        QMessageBox.critical(
            self.main_window if self.main_window else None,
            title,
            message
        )
        
        # 어플리케이션 종료
        QApplication.quit()
        
    def check_dependencies(self) -> Dict[str, bool]:
        """의존성 확인"""
        dependencies = {}
        
        # 필수 모듈 확인
        required_modules = [
            'PyQt5',
            'pyqtgraph',
            'pandas',
            'numpy',
            'matplotlib'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
                dependencies[module] = True
            except ImportError:
                dependencies[module] = False
                self.logger.error(f"Missing required module: {module}")
                
        return dependencies
        
    def cleanup(self):
        """리소스 정리"""
        # 윈도우 상태 저장
        self.save_window_state()
        
        # 리소스 정리
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, 'close'):
                    resource.close()
            except Exception as e:
                self.logger.error(f"Failed to cleanup resource {name}: {str(e)}")
                
        self._resources.clear()
        
    def detect_wsl2(self) -> bool:
        """WSL2 환경 감지"""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except:
            return False
    
    def run(self) -> int:
        """어플리케이션 실행"""
        # WSL2 환경 체크
        if self.detect_wsl2():
            self.logger.info("WSL2 환경에서 실행 중")
            # DISPLAY 환경변수 확인
            if not os.environ.get('DISPLAY'):
                self.logger.warning("DISPLAY 환경변수가 설정되지 않았습니다")
                print("\n⚠️  WSL2 환경에서 GUI를 표시하려면 X11 서버 설정이 필요합니다.")
                print("   ./setup_x11_wsl2.sh 스크립트를 실행하여 설정하세요.\n")
        
        # QApplication 생성 또는 가져오기
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        # 어플리케이션 정보 설정
        app.setApplicationName(self.name)
        app.setApplicationDisplayName(self.name)
        app.setOrganizationName("KStock")
        
        # 테마 설정
        self.setup_theme()
        
        # 예외 처리기 설정
        self.setup_exception_handler()
        
        # 의존성 확인
        deps = self.check_dependencies()
        missing_deps = [name for name, available in deps.items() if not available]
        if missing_deps:
            self.handle_fatal_error(
                "의존성 오류",
                f"다음 모듈이 설치되지 않았습니다:\n{', '.join(missing_deps)}"
            )
            return 1
            
        # 메인 윈도우 생성 및 표시
        self.create_main_window()
        self.main_window.show()
        
        # 이벤트 루프 실행
        result = app.exec_()
        
        # 정리
        self.cleanup()
        
        return result


def main():
    """메인 진입점"""
    app = TradingApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()