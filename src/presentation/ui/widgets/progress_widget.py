# -*- coding: utf-8 -*-
"""
백테스트 진행률 표시 위젯
"""
import time
from datetime import datetime, timedelta
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QPushButton,
    QGroupBox, QGridLayout, QFrame
)
from PyQt5.QtGui import QPalette, QColor


class ProgressWidget(QWidget):
    """백테스트 진행률 표시 위젯"""
    
    # 시그널
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        """위젯 초기화"""
        super().__init__(parent)
        self._start_time: Optional[float] = None
        self._is_paused = False
        self._elapsed_time = 0
        self._pause_start_time: Optional[float] = None
        
        self._init_ui()
        self._setup_timer()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 제목
        title = QLabel("백테스트 진행 상황")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 상태 정보
        info_layout = QGridLayout()
        
        # 현재 단계
        self.stage_label = QLabel("준비 중...")
        self.stage_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(QLabel("현재 단계:"), 0, 0)
        info_layout.addWidget(self.stage_label, 0, 1)
        
        # 처리 중인 날짜
        self.current_date_label = QLabel("-")
        info_layout.addWidget(QLabel("처리 날짜:"), 1, 0)
        info_layout.addWidget(self.current_date_label, 1, 1)
        
        # 경과 시간
        self.elapsed_time_label = QLabel("00:00:00")
        info_layout.addWidget(QLabel("경과 시간:"), 0, 2)
        info_layout.addWidget(self.elapsed_time_label, 0, 3)
        
        # 예상 남은 시간
        self.remaining_time_label = QLabel("-")
        info_layout.addWidget(QLabel("남은 시간:"), 1, 2)
        info_layout.addWidget(self.remaining_time_label, 1, 3)
        
        # 처리 속도
        self.speed_label = QLabel("0 일/초")
        info_layout.addWidget(QLabel("처리 속도:"), 2, 0)
        info_layout.addWidget(self.speed_label, 2, 1)
        
        # 메모리 사용량
        self.memory_label = QLabel("0 MB")
        info_layout.addWidget(QLabel("메모리:"), 2, 2)
        info_layout.addWidget(self.memory_label, 2, 3)
        
        layout.addLayout(info_layout)
        
        # 상세 정보 그룹
        detail_group = QGroupBox("상세 정보")
        detail_layout = QGridLayout()
        
        # 처리된 거래 수
        self.trades_label = QLabel("0")
        detail_layout.addWidget(QLabel("거래 수:"), 0, 0)
        detail_layout.addWidget(self.trades_label, 0, 1)
        
        # 현재 포지션 수
        self.positions_label = QLabel("0")
        detail_layout.addWidget(QLabel("포지션:"), 0, 2)
        detail_layout.addWidget(self.positions_label, 0, 3)
        
        # 현재 수익률
        self.return_label = QLabel("0.00%")
        self.return_label.setStyleSheet("font-weight: bold;")
        detail_layout.addWidget(QLabel("수익률:"), 1, 0)
        detail_layout.addWidget(self.return_label, 1, 1)
        
        # 현재 자산
        self.equity_label = QLabel("0")
        detail_layout.addWidget(QLabel("총 자산:"), 1, 2)
        detail_layout.addWidget(self.equity_label, 1, 3)
        
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)
        
        # 컨트롤 버튼
        button_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("일시정지")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #f44336;
                color: white;
            }
            QPushButton:enabled:hover {
                background-color: #da190b;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def _setup_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_elapsed_time)
        self.update_timer.setInterval(100)  # 100ms마다 업데이트
        
    def _update_elapsed_time(self):
        """경과 시간 업데이트"""
        if self._start_time and not self._is_paused:
            self._elapsed_time = time.time() - self._start_time
            hours = int(self._elapsed_time // 3600)
            minutes = int((self._elapsed_time % 3600) // 60)
            seconds = int(self._elapsed_time % 60)
            
            self.elapsed_time_label.setText(
                f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            )
            
    def _on_pause_clicked(self):
        """일시정지 버튼 클릭"""
        if self._is_paused:
            # 재개
            if self._pause_start_time:
                pause_duration = time.time() - self._pause_start_time
                self._start_time += pause_duration
            
            self._is_paused = False
            self.pause_btn.setText("일시정지")
            self.update_timer.start()
            self.resume_requested.emit()
        else:
            # 일시정지
            self._is_paused = True
            self._pause_start_time = time.time()
            self.pause_btn.setText("재개")
            self.update_timer.stop()
            self.pause_requested.emit()
            
    def _on_stop_clicked(self):
        """중지 버튼 클릭"""
        self.stop_requested.emit()
        
    def start(self):
        """진행률 추적 시작"""
        self._start_time = time.time()
        self._elapsed_time = 0
        self._is_paused = False
        
        self.progress_bar.setValue(0)
        self.stage_label.setText("백테스트 시작")
        
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.update_timer.start()
        
    def stop(self):
        """진행률 추적 중지"""
        self.update_timer.stop()
        
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        if self._start_time:
            total_time = time.time() - self._start_time
            self.stage_label.setText(f"완료 (총 {total_time:.1f}초)")
            
    def update_progress(self, progress: float, message: str = ""):
        """진행률 업데이트
        
        Args:
            progress: 진행률 (0.0 ~ 1.0)
            message: 상태 메시지
        """
        # 진행률 바 업데이트
        self.progress_bar.setValue(int(progress * 100))
        
        # 상태 메시지
        if message:
            self.stage_label.setText(message)
            
        # 남은 시간 예측
        if self._start_time and progress > 0:
            elapsed = time.time() - self._start_time
            if progress < 1.0:
                total_estimated = elapsed / progress
                remaining = total_estimated - elapsed
                
                if remaining > 0:
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    seconds = int(remaining % 60)
                    
                    self.remaining_time_label.setText(
                        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    )
                else:
                    self.remaining_time_label.setText("거의 완료")
            else:
                self.remaining_time_label.setText("완료")
                
    def update_date(self, current_date: datetime):
        """현재 처리 중인 날짜 업데이트"""
        self.current_date_label.setText(current_date.strftime("%Y-%m-%d"))
        
    def update_speed(self, days_per_second: float):
        """처리 속도 업데이트"""
        self.speed_label.setText(f"{days_per_second:.1f} 일/초")
        
    def update_memory(self, memory_mb: float):
        """메모리 사용량 업데이트"""
        self.memory_label.setText(f"{memory_mb:.1f} MB")
        
    def update_trades(self, trade_count: int):
        """거래 수 업데이트"""
        self.trades_label.setText(f"{trade_count:,}")
        
    def update_positions(self, position_count: int):
        """포지션 수 업데이트"""
        self.positions_label.setText(f"{position_count:,}")
        
    def update_performance(self, return_pct: float, equity: float):
        """성과 업데이트"""
        # 수익률
        self.return_label.setText(f"{return_pct:+.2f}%")
        
        if return_pct > 0:
            self.return_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif return_pct < 0:
            self.return_label.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.return_label.setStyleSheet("font-weight: bold;")
            
        # 자산
        self.equity_label.setText(f"{equity:,.0f}")
        
    def set_indeterminate(self, indeterminate: bool = True):
        """불확정 모드 설정 (진행률을 알 수 없을 때)"""
        if indeterminate:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setMinimum(0)
        else:
            self.progress_bar.setMaximum(100)
            self.progress_bar.setMinimum(0)