# -*- coding: utf-8 -*-
"""
백테스트 설정 위젯
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QTextEdit,
    QSizePolicy
)


class BacktestConfigWidget(QWidget):
    """백테스트 설정 위젯"""
    
    # 시그널
    config_changed = pyqtSignal(dict)
    run_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        """위젯 초기화"""
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self._load_defaults()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 기간 설정
        period_group = self._create_period_group()
        layout.addWidget(period_group)
        
        # 자본금 설정
        capital_group = self._create_capital_group()
        layout.addWidget(capital_group)
        
        # 거래 비용 설정
        cost_group = self._create_cost_group()
        layout.addWidget(cost_group)
        
        # 리스크 설정
        risk_group = self._create_risk_group()
        layout.addWidget(risk_group)
        
        # 실행 옵션
        options_group = self._create_options_group()
        layout.addWidget(options_group)
        
        # 실행 버튼
        button_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("검증")
        self.validate_btn.setObjectName("validateButton")
        
        self.run_btn = QPushButton("백테스트 실행")
        self.run_btn.setObjectName("runButton")
        self.run_btn.setStyleSheet("""
            QPushButton#runButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton#runButton:hover {
                background-color: #45a049;
            }
        """)
        
        button_layout.addWidget(self.validate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.run_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
    def _create_period_group(self) -> QGroupBox:
        """기간 설정 그룹 생성"""
        group = QGroupBox("백테스트 기간")
        layout = QFormLayout()
        
        # 시작일
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        
        # 종료일
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        
        # 기간 정보
        self.period_info = QLabel()
        self.period_info.setStyleSheet("color: #888888;")
        
        layout.addRow("시작일:", self.start_date)
        layout.addRow("종료일:", self.end_date)
        layout.addRow("", self.period_info)
        
        group.setLayout(layout)
        return group
        
    def _create_capital_group(self) -> QGroupBox:
        """자본금 설정 그룹 생성"""
        group = QGroupBox("자본금 설정")
        layout = QFormLayout()
        
        # 초기 자본금
        self.initial_capital = QLineEdit()
        self.initial_capital.setText("10,000,000")
        self.initial_capital.setAlignment(Qt.AlignRight)
        
        # 통화
        self.currency = QComboBox()
        self.currency.addItems(["KRW", "USD"])
        
        # 레버리지
        self.leverage = QDoubleSpinBox()
        self.leverage.setRange(1.0, 10.0)
        self.leverage.setSingleStep(0.5)
        self.leverage.setValue(1.0)
        self.leverage.setSuffix("x")
        
        layout.addRow("초기 자본금:", self.initial_capital)
        layout.addRow("통화:", self.currency)
        layout.addRow("레버리지:", self.leverage)
        
        group.setLayout(layout)
        return group
        
    def _create_cost_group(self) -> QGroupBox:
        """거래 비용 설정 그룹 생성"""
        group = QGroupBox("거래 비용")
        layout = QFormLayout()
        
        # 수수료율
        self.commission_rate = QDoubleSpinBox()
        self.commission_rate.setRange(0.0, 1.0)
        self.commission_rate.setSingleStep(0.01)
        self.commission_rate.setValue(0.15)
        self.commission_rate.setSuffix("%")
        self.commission_rate.setDecimals(3)
        
        # 세금율 (매도시)
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0.0, 1.0)
        self.tax_rate.setSingleStep(0.01)
        self.tax_rate.setValue(0.3)
        self.tax_rate.setSuffix("%")
        self.tax_rate.setDecimals(3)
        
        # 슬리피지
        self.slippage_rate = QDoubleSpinBox()
        self.slippage_rate.setRange(0.0, 1.0)
        self.slippage_rate.setSingleStep(0.01)
        self.slippage_rate.setValue(0.1)
        self.slippage_rate.setSuffix("%")
        self.slippage_rate.setDecimals(3)
        
        # 최소 수수료
        self.min_commission = QLineEdit()
        self.min_commission.setText("1,000")
        self.min_commission.setAlignment(Qt.AlignRight)
        
        layout.addRow("수수료율:", self.commission_rate)
        layout.addRow("세금율:", self.tax_rate)
        layout.addRow("슬리피지:", self.slippage_rate)
        layout.addRow("최소 수수료:", self.min_commission)
        
        group.setLayout(layout)
        return group
        
    def _create_risk_group(self) -> QGroupBox:
        """리스크 설정 그룹 생성"""
        group = QGroupBox("리스크 관리")
        layout = QFormLayout()
        
        # 최대 포지션 크기
        self.max_position_size = QDoubleSpinBox()
        self.max_position_size.setRange(0.0, 100.0)
        self.max_position_size.setSingleStep(5.0)
        self.max_position_size.setValue(20.0)
        self.max_position_size.setSuffix("%")
        
        # 최대 섹터 노출
        self.max_sector_exposure = QDoubleSpinBox()
        self.max_sector_exposure.setRange(0.0, 100.0)
        self.max_sector_exposure.setSingleStep(5.0)
        self.max_sector_exposure.setValue(30.0)
        self.max_sector_exposure.setSuffix("%")
        
        # 최대 포지션 수
        self.max_positions = QSpinBox()
        self.max_positions.setRange(1, 100)
        self.max_positions.setValue(10)
        
        # 손절 비율
        self.stop_loss = QDoubleSpinBox()
        self.stop_loss.setRange(0.0, 50.0)
        self.stop_loss.setSingleStep(1.0)
        self.stop_loss.setValue(5.0)
        self.stop_loss.setSuffix("%")
        
        layout.addRow("최대 포지션 크기:", self.max_position_size)
        layout.addRow("최대 섹터 노출:", self.max_sector_exposure)
        layout.addRow("최대 포지션 수:", self.max_positions)
        layout.addRow("손절 비율:", self.stop_loss)
        
        group.setLayout(layout)
        return group
        
    def _create_options_group(self) -> QGroupBox:
        """실행 옵션 그룹 생성"""
        group = QGroupBox("실행 옵션")
        layout = QVBoxLayout()
        
        # 체크박스 옵션
        self.enable_short = QCheckBox("공매도 허용")
        self.enable_margin = QCheckBox("신용거래 허용")
        self.reinvest_dividends = QCheckBox("배당금 재투자")
        self.reinvest_dividends.setChecked(True)
        
        self.use_adjusted_price = QCheckBox("수정주가 사용")
        self.use_adjusted_price.setChecked(True)
        
        self.save_trades = QCheckBox("거래 내역 저장")
        self.save_trades.setChecked(True)
        
        layout.addWidget(self.enable_short)
        layout.addWidget(self.enable_margin)
        layout.addWidget(self.reinvest_dividends)
        layout.addWidget(self.use_adjusted_price)
        layout.addWidget(self.save_trades)
        
        # 설명
        self.description = QTextEdit()
        self.description.setPlaceholderText("백테스트 설명 (선택사항)")
        self.description.setMaximumHeight(80)
        
        layout.addWidget(QLabel("설명:"))
        layout.addWidget(self.description)
        
        group.setLayout(layout)
        return group
        
    def _connect_signals(self):
        """시그널 연결"""
        # 날짜 변경 시 기간 정보 업데이트
        self.start_date.dateChanged.connect(self._update_period_info)
        self.end_date.dateChanged.connect(self._update_period_info)
        
        # 설정 변경 시
        self.initial_capital.textChanged.connect(self._on_config_changed)
        self.commission_rate.valueChanged.connect(self._on_config_changed)
        self.tax_rate.valueChanged.connect(self._on_config_changed)
        self.slippage_rate.valueChanged.connect(self._on_config_changed)
        
        # 버튼 클릭
        self.validate_btn.clicked.connect(self._validate_config)
        self.run_btn.clicked.connect(self._on_run_clicked)
        
    def _load_defaults(self):
        """기본값 로드"""
        # 기간: 최근 1년
        today = QDate.currentDate()
        self.end_date.setDate(today)
        self.start_date.setDate(today.addYears(-1))
        
        self._update_period_info()
        
    def _update_period_info(self):
        """기간 정보 업데이트"""
        start = self.start_date.date()
        end = self.end_date.date()
        
        days = start.daysTo(end)
        if days < 0:
            self.period_info.setText("⚠️ 종료일이 시작일보다 이전입니다")
            self.period_info.setStyleSheet("color: #ff5555;")
        else:
            years = days / 365.25
            self.period_info.setText(
                f"기간: {days}일 ({years:.1f}년)"
            )
            self.period_info.setStyleSheet("color: #888888;")
            
    def _on_config_changed(self):
        """설정 변경 시"""
        config = self.get_config()
        self.config_changed.emit(config)
        
    def _validate_config(self) -> bool:
        """설정 검증"""
        errors = []
        
        # 날짜 검증
        if self.start_date.date() >= self.end_date.date():
            errors.append("종료일은 시작일 이후여야 합니다")
            
        # 자본금 검증
        try:
            capital = self._parse_money(self.initial_capital.text())
            if capital <= 0:
                errors.append("초기 자본금은 0보다 커야 합니다")
        except:
            errors.append("올바른 자본금을 입력하세요")
            
        # 에러 표시
        if errors:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "설정 오류",
                "\n".join(errors)
            )
            return False
            
        return True
        
    def _on_run_clicked(self):
        """실행 버튼 클릭 시"""
        if self._validate_config():
            config = self.get_config()
            self.run_requested.emit(config)
            
    def _parse_money(self, text: str) -> int:
        """금액 문자열 파싱"""
        # 쉼표 제거
        return int(text.replace(",", ""))
        
    def _format_money(self, value: int) -> str:
        """금액 포맷팅"""
        return f"{value:,}"
        
    def get_config(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return {
            # 기간
            "start_date": self.start_date.date().toPyDate(),
            "end_date": self.end_date.date().toPyDate(),
            
            # 자본금
            "initial_capital": Decimal(str(self._parse_money(
                self.initial_capital.text()
            ))),
            "currency": self.currency.currentText(),
            "leverage": Decimal(str(self.leverage.value())),
            
            # 거래 비용
            "commission_rate": Decimal(str(self.commission_rate.value() / 100)),
            "tax_rate": Decimal(str(self.tax_rate.value() / 100)),
            "slippage_rate": Decimal(str(self.slippage_rate.value() / 100)),
            "min_commission": Decimal(str(self._parse_money(
                self.min_commission.text()
            ))),
            
            # 리스크
            "max_position_size": self.max_position_size.value() / 100,
            "max_sector_exposure": self.max_sector_exposure.value() / 100,
            "max_positions": self.max_positions.value(),
            "stop_loss": self.stop_loss.value() / 100,
            
            # 옵션
            "enable_short": self.enable_short.isChecked(),
            "enable_margin": self.enable_margin.isChecked(),
            "reinvest_dividends": self.reinvest_dividends.isChecked(),
            "use_adjusted_price": self.use_adjusted_price.isChecked(),
            "save_trades": self.save_trades.isChecked(),
            
            # 설명
            "description": self.description.toPlainText()
        }
        
    def set_config(self, config: Dict[str, Any]):
        """설정 적용"""
        # 기간
        if "start_date" in config:
            self.start_date.setDate(QDate(config["start_date"]))
        if "end_date" in config:
            self.end_date.setDate(QDate(config["end_date"]))
            
        # 자본금
        if "initial_capital" in config:
            self.initial_capital.setText(
                self._format_money(int(config["initial_capital"]))
            )
        if "leverage" in config:
            self.leverage.setValue(float(config["leverage"]))
            
        # 거래 비용
        if "commission_rate" in config:
            self.commission_rate.setValue(float(config["commission_rate"]) * 100)
        if "tax_rate" in config:
            self.tax_rate.setValue(float(config["tax_rate"]) * 100)
        if "slippage_rate" in config:
            self.slippage_rate.setValue(float(config["slippage_rate"]) * 100)
            
        # 리스크
        if "max_position_size" in config:
            self.max_position_size.setValue(config["max_position_size"] * 100)
        if "max_positions" in config:
            self.max_positions.setValue(config["max_positions"])
            
        # 옵션
        if "enable_short" in config:
            self.enable_short.setChecked(config["enable_short"])
        if "reinvest_dividends" in config:
            self.reinvest_dividends.setChecked(config["reinvest_dividends"])