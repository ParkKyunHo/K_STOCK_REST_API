#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI 테스트 스크립트
"""
import sys
import os

# UTF-8 인코딩 설정
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('utf-8')

# 환경 변수 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'ko_KR.UTF-8'
os.environ['LC_ALL'] = 'ko_KR.UTF-8'

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from src.presentation.ui.main_window import MainWindow

def test_main_window():
    """메인 윈도우 테스트"""
    app = QApplication(sys.argv)
    
    # 한글 폰트 설정
    from PyQt5.QtGui import QFont, QFontDatabase
    
    # 사용 가능한 폰트 확인
    font_db = QFontDatabase()
    available_fonts = font_db.families()
    
    # Linux용 한글 폰트 우선순위
    korean_fonts = [
        "Noto Sans CJK KR",
        "NanumGothic", 
        "Nanum Gothic",
        "NanumBarunGothic",
        "Malgun Gothic",
        "맑은 고딕",
        "UnDotum",
        "DejaVu Sans"
    ]
    
    font = QFont()
    font_set = False
    
    if sys.platform == "linux":
        # 사용 가능한 한글 폰트 찾기
        for font_name in korean_fonts:
            if font_name in available_fonts:
                font.setFamily(font_name)
                font_set = True
                print(f"한글 폰트 설정: {font_name}")
                break
        
        if not font_set:
            # 기본 폰트 사용
            font.setFamily("DejaVu Sans")
            print("경고: 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
    elif sys.platform == "win32":
        font.setFamily("맑은 고딕")
    elif sys.platform == "darwin":
        font.setFamily("Apple SD Gothic Neo")
    
    font.setPointSize(10)
    app.setFont(font)
    
    # 메인 윈도우 생성
    window = MainWindow()
    window.show()
    
    # 로그 메시지 추가 테스트
    window.add_log_message("어플리케이션 시작됨", "INFO")
    window.add_log_message("UI 초기화 완료", "DEBUG")
    window.add_log_message("경고: 테스트 메시지", "WARNING")
    window.add_log_message("오류: 테스트 에러", "ERROR")
    
    # 상태바 메시지
    window.show_status_message("UI 테스트 중...")
    
    # 샘플 전략 로드
    window.load_sample_strategies()
    
    # 어플리케이션 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_main_window()