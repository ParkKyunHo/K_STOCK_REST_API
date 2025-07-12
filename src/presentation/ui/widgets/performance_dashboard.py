# -*- coding: utf-8 -*-
"""
성과 지표 대시보드 위젯
"""
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox
)


class MetricCard(QFrame):
    """개별 성과 지표 카드 위젯"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.title = title
        self._init_ui()
        self._setup_style()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 제목
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.title_label.setFont(font)
        
        # 값
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.value_label.setFont(font)
        
        # 부가 정보 (선택적)
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(8)
        self.detail_label.setFont(font)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)
    
    def _setup_style(self):
        """스타일 설정"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(1)
    
    def update_value(self, value: str, detail: str = "", color: str = "#FFFFFF"):
        """값 업데이트"""
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f"color: {color};")
        self.detail_label.setText(detail)


class PerformanceGauge(QWidget):
    """성과 게이지 위젯 (진행률 바 형태)"""
    
    def __init__(self, title: str, min_val: float = 0, max_val: float = 100, parent=None):
        super().__init__(parent)
        self.setObjectName("performanceGauge")
        self.title = title
        self.min_val = min_val
        self.max_val = max_val
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 제목
        self.title_label = QLabel(self.title)
        font = QFont()
        font.setPointSize(9)
        self.title_label.setFont(font)
        
        # 게이지 (진행률 바)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(int(self.min_val))
        self.progress_bar.setMaximum(int(self.max_val))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        # 값 표시
        self.value_label = QLabel("0.00")
        self.value_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(8)
        self.value_label.setFont(font)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.value_label)
    
    def update_value(self, value: float, suffix: str = "%"):
        """값 업데이트"""
        # 정규화
        normalized_value = max(self.min_val, min(self.max_val, value))
        self.progress_bar.setValue(int(normalized_value))
        self.value_label.setText(f"{value:.2f}{suffix}")
        
        # 색상 설정
        if value < 0:
            color = "#FF4444"  # 빨간색
        elif value < 10:
            color = "#FFA500"  # 주황색
        else:
            color = "#4CAF50"  # 녹색
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)


class PerformanceDashboard(QWidget):
    """성과 지표 대시보드 메인 위젯"""
    
    # 시그널
    refresh_requested = pyqtSignal()
    export_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("performanceDashboard")
        self._init_ui()
        self._init_default_data()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # 제목
        title_label = QLabel("백테스트 성과 분석")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 주요 지표 카드들
        self._create_metric_cards(main_layout)
        
        # 게이지들
        self._create_gauges(main_layout)
        
        # 상세 테이블
        self._create_detail_table(main_layout)
    
    def _create_metric_cards(self, parent_layout):
        """주요 지표 카드 생성"""
        cards_group = QGroupBox("주요 성과 지표")
        cards_layout = QGridLayout(cards_group)
        cards_layout.setSpacing(10)
        
        # 카드 생성
        self.total_return_card = MetricCard("총 수익률")
        self.annual_return_card = MetricCard("연환산 수익률")
        self.sharpe_ratio_card = MetricCard("샤프 비율")
        self.max_drawdown_card = MetricCard("최대 낙폭")
        self.win_rate_card = MetricCard("승률")
        self.profit_factor_card = MetricCard("수익 인수")
        
        # 배치 (2x3 그리드)
        cards_layout.addWidget(self.total_return_card, 0, 0)
        cards_layout.addWidget(self.annual_return_card, 0, 1)
        cards_layout.addWidget(self.sharpe_ratio_card, 0, 2)
        cards_layout.addWidget(self.max_drawdown_card, 1, 0)
        cards_layout.addWidget(self.win_rate_card, 1, 1)
        cards_layout.addWidget(self.profit_factor_card, 1, 2)
        
        parent_layout.addWidget(cards_group)
    
    def _create_gauges(self, parent_layout):
        """게이지 생성"""
        gauges_group = QGroupBox("위험 지표")
        gauges_layout = QHBoxLayout(gauges_group)
        gauges_layout.setSpacing(15)
        
        # 게이지 생성
        self.volatility_gauge = PerformanceGauge("변동성", 0, 50)
        self.beta_gauge = PerformanceGauge("베타", 0, 2)
        self.var_gauge = PerformanceGauge("VaR (95%)", 0, 10)
        
        gauges_layout.addWidget(self.volatility_gauge)
        gauges_layout.addWidget(self.beta_gauge)
        gauges_layout.addWidget(self.var_gauge)
        
        parent_layout.addWidget(gauges_group)
    
    def _create_detail_table(self, parent_layout):
        """상세 통계 테이블 생성"""
        table_group = QGroupBox("상세 통계")
        table_layout = QVBoxLayout(table_group)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(2)
        self.detail_table.setHorizontalHeaderLabels(["지표", "값"])
        
        # 헤더 설정
        header = self.detail_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # 행 높이 설정
        self.detail_table.verticalHeader().setDefaultSectionSize(25)
        self.detail_table.verticalHeader().setVisible(False)
        
        # 선택 모드 설정
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        
        table_layout.addWidget(self.detail_table)
        parent_layout.addWidget(table_group)
    
    def _init_default_data(self):
        """기본 데이터 초기화"""
        # 기본값으로 초기화
        self.update_performance_data({})
    
    def update_performance_data(self, data: Dict[str, Any]):
        """성과 데이터 업데이트"""
        # 주요 지표 카드 업데이트
        total_return = data.get('total_return', 0.0)
        annual_return = data.get('annual_return', 0.0)
        sharpe_ratio = data.get('sharpe_ratio', 0.0)
        max_drawdown = data.get('max_drawdown', 0.0)
        win_rate = data.get('win_rate', 0.0)
        profit_factor = data.get('profit_factor', 0.0)
        
        # 색상 결정
        return_color = "#4CAF50" if total_return >= 0 else "#FF4444"
        sharpe_color = "#4CAF50" if sharpe_ratio >= 1.0 else "#FFA500" if sharpe_ratio >= 0.5 else "#FF4444"
        drawdown_color = "#4CAF50" if max_drawdown >= -5 else "#FFA500" if max_drawdown >= -15 else "#FF4444"
        
        self.total_return_card.update_value(
            f"{total_return:.2f}%", 
            f"기간: {data.get('period_days', 0)}일",
            return_color
        )
        
        self.annual_return_card.update_value(
            f"{annual_return:.2f}%",
            "연환산 기준",
            return_color
        )
        
        self.sharpe_ratio_card.update_value(
            f"{sharpe_ratio:.2f}",
            "위험조정수익률",
            sharpe_color
        )
        
        self.max_drawdown_card.update_value(
            f"{max_drawdown:.2f}%",
            "최대 손실폭",
            drawdown_color
        )
        
        self.win_rate_card.update_value(
            f"{win_rate:.1f}%",
            f"{data.get('total_trades', 0)}회 거래"
        )
        
        self.profit_factor_card.update_value(
            f"{profit_factor:.2f}",
            "손익비"
        )
        
        # 게이지 업데이트
        volatility = data.get('volatility', 0.0) * 100  # %로 변환
        beta = data.get('beta', 1.0)
        var_95 = abs(data.get('var_95', 0.0)) * 100  # %로 변환
        
        self.volatility_gauge.update_value(volatility)
        self.beta_gauge.update_value(beta, "")
        self.var_gauge.update_value(var_95)
        
        # 상세 테이블 업데이트
        self._update_detail_table(data)
    
    def _update_detail_table(self, data: Dict[str, Any]):
        """상세 테이블 업데이트"""
        details = [
            ("시작일", data.get('start_date', '--')),
            ("종료일", data.get('end_date', '--')),
            ("거래 기간", f"{data.get('period_days', 0)}일"),
            ("초기 자본", f"{data.get('initial_capital', 0):,.0f}원"),
            ("최종 자본", f"{data.get('final_capital', 0):,.0f}원"),
            ("총 거래 횟수", f"{data.get('total_trades', 0)}회"),
            ("수익 거래", f"{data.get('winning_trades', 0)}회"),
            ("손실 거래", f"{data.get('losing_trades', 0)}회"),
            ("평균 수익률", f"{data.get('avg_return', 0.0):.2f}%"),
            ("표준편차", f"{data.get('volatility', 0.0)*100:.2f}%"),
            ("최대 수익", f"{data.get('max_win', 0.0):.2f}%"),
            ("최대 손실", f"{data.get('max_loss', 0.0):.2f}%"),
            ("소르티노 비율", f"{data.get('sortino_ratio', 0.0):.2f}"),
            ("칼마 비율", f"{data.get('calmar_ratio', 0.0):.2f}"),
            ("VaR (99%)", f"{abs(data.get('var_99', 0.0))*100:.2f}%"),
            ("CVaR (95%)", f"{abs(data.get('cvar_95', 0.0))*100:.2f}%"),
        ]
        
        self.detail_table.setRowCount(len(details))
        
        for i, (label, value) in enumerate(details):
            # 라벨
            label_item = QTableWidgetItem(label)
            label_item.setFlags(Qt.ItemIsEnabled)
            self.detail_table.setItem(i, 0, label_item)
            
            # 값
            value_item = QTableWidgetItem(str(value))
            value_item.setFlags(Qt.ItemIsEnabled)
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.detail_table.setItem(i, 1, value_item)
    
    def get_summary_data(self) -> Dict[str, Any]:
        """요약 데이터 반환"""
        return {
            "total_return": self.total_return_card.value_label.text(),
            "sharpe_ratio": self.sharpe_ratio_card.value_label.text(),
            "max_drawdown": self.max_drawdown_card.value_label.text(),
            "win_rate": self.win_rate_card.value_label.text(),
            "timestamp": datetime.now().isoformat()
        }