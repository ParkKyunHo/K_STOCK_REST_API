# -*- coding: utf-8 -*-
"""
성과 대시보드 위젯 테스트
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from src.presentation.ui.widgets.performance_dashboard import (
    MetricCard, PerformanceGauge, PerformanceDashboard
)


@pytest.fixture
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMetricCard:
    """MetricCard 위젯 테스트"""
    
    def test_metric_card_initialization(self, qapp):
        """MetricCard 초기화 테스트"""
        card = MetricCard("Test Metric")
        
        assert card.title == "Test Metric"
        assert card.title_label.text() == "Test Metric"
        assert card.value_label.text() == "--"
        assert card.detail_label.text() == ""
    
    def test_metric_card_update_value(self, qapp):
        """MetricCard 값 업데이트 테스트"""
        card = MetricCard("Total Return")
        
        # 값 업데이트
        card.update_value("15.50%", "1년 기간", "#4CAF50")
        
        assert card.value_label.text() == "15.50%"
        assert card.detail_label.text() == "1년 기간"
        assert "#4CAF50" in card.value_label.styleSheet()
    
    def test_metric_card_negative_value(self, qapp):
        """MetricCard 음수 값 테스트"""
        card = MetricCard("Max Drawdown")
        
        card.update_value("-8.50%", "최대 손실", "#FF4444")
        
        assert card.value_label.text() == "-8.50%"
        assert "#FF4444" in card.value_label.styleSheet()


class TestPerformanceGauge:
    """PerformanceGauge 위젯 테스트"""
    
    def test_gauge_initialization(self, qapp):
        """PerformanceGauge 초기화 테스트"""
        gauge = PerformanceGauge("Volatility", 0, 50)
        
        assert gauge.title == "Volatility"
        assert gauge.min_val == 0
        assert gauge.max_val == 50
        assert gauge.progress_bar.minimum() == 0
        assert gauge.progress_bar.maximum() == 50
    
    def test_gauge_update_value(self, qapp):
        """PerformanceGauge 값 업데이트 테스트"""
        gauge = PerformanceGauge("Win Rate", 0, 100)
        
        gauge.update_value(65.5, "%")
        
        assert gauge.progress_bar.value() == 65
        assert gauge.value_label.text() == "65.50%"
    
    def test_gauge_value_normalization(self, qapp):
        """PerformanceGauge 값 정규화 테스트"""
        gauge = PerformanceGauge("Beta", 0, 2)
        
        # 범위를 벗어나는 값 테스트
        gauge.update_value(5.0, "")  # max_val을 초과
        assert gauge.progress_bar.value() == 2
        
        gauge.update_value(-1.0, "")  # min_val 미만
        assert gauge.progress_bar.value() == 0
    
    def test_gauge_color_coding(self, qapp):
        """PerformanceGauge 색상 코딩 테스트"""
        gauge = PerformanceGauge("Return", -50, 50)
        
        # 음수 값 (빨간색)
        gauge.update_value(-10.0)
        assert "#FF4444" in gauge.progress_bar.styleSheet()
        
        # 낮은 양수 값 (주황색)
        gauge.update_value(5.0)
        assert "#FFA500" in gauge.progress_bar.styleSheet()
        
        # 높은 양수 값 (녹색)
        gauge.update_value(15.0)
        assert "#4CAF50" in gauge.progress_bar.styleSheet()


class TestPerformanceDashboard:
    """PerformanceDashboard 메인 위젯 테스트"""
    
    def test_dashboard_initialization(self, qapp):
        """PerformanceDashboard 초기화 테스트"""
        dashboard = PerformanceDashboard()
        
        # 메인 컴포넌트들이 생성되었는지 확인
        assert dashboard.total_return_card is not None
        assert dashboard.sharpe_ratio_card is not None
        assert dashboard.max_drawdown_card is not None
        assert dashboard.win_rate_card is not None
        assert dashboard.profit_factor_card is not None
        assert dashboard.annual_return_card is not None
        
        assert dashboard.volatility_gauge is not None
        assert dashboard.beta_gauge is not None
        assert dashboard.var_gauge is not None
        
        assert dashboard.detail_table is not None
    
    def test_dashboard_update_performance_data(self, qapp):
        """PerformanceDashboard 성과 데이터 업데이트 테스트"""
        dashboard = PerformanceDashboard()
        
        sample_data = {
            'total_return': 15.5,
            'annual_return': 15.0,
            'sharpe_ratio': 1.85,
            'max_drawdown': -8.5,
            'win_rate': 65.2,
            'profit_factor': 1.42,
            'volatility': 0.18,
            'beta': 0.95,
            'var_95': -0.035,
            'period_days': 365,
            'total_trades': 156,
            'initial_capital': 10000000,
            'final_capital': 11550000
        }
        
        dashboard.update_performance_data(sample_data)
        
        # 카드 값들이 업데이트되었는지 확인
        assert "15.50%" in dashboard.total_return_card.value_label.text()
        assert "15.00%" in dashboard.annual_return_card.value_label.text()
        assert "1.85" in dashboard.sharpe_ratio_card.value_label.text()
        assert "-8.50%" in dashboard.max_drawdown_card.value_label.text()
        assert "65.2%" in dashboard.win_rate_card.value_label.text()
        assert "1.42" in dashboard.profit_factor_card.value_label.text()
    
    def test_dashboard_empty_data_handling(self, qapp):
        """PerformanceDashboard 빈 데이터 처리 테스트"""
        dashboard = PerformanceDashboard()
        
        # 빈 딕셔너리로 업데이트
        dashboard.update_performance_data({})
        
        # 기본값들이 표시되는지 확인
        assert "0.00%" in dashboard.total_return_card.value_label.text()
        assert "0.00" in dashboard.sharpe_ratio_card.value_label.text()
    
    def test_dashboard_detail_table_update(self, qapp):
        """PerformanceDashboard 상세 테이블 업데이트 테스트"""
        dashboard = PerformanceDashboard()
        
        sample_data = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'period_days': 365,
            'initial_capital': 10000000,
            'final_capital': 11550000,
            'total_trades': 156,
            'winning_trades': 102,
            'losing_trades': 54
        }
        
        dashboard.update_performance_data(sample_data)
        
        # 테이블 행 수 확인
        assert dashboard.detail_table.rowCount() > 0
        
        # 특정 값들이 테이블에 있는지 확인
        table_text = ""
        for row in range(dashboard.detail_table.rowCount()):
            for col in range(dashboard.detail_table.columnCount()):
                item = dashboard.detail_table.item(row, col)
                if item:
                    table_text += item.text() + " "
        
        assert "2024-01-01" in table_text
        assert "365일" in table_text
        assert "156회" in table_text
    
    def test_dashboard_get_summary_data(self, qapp):
        """PerformanceDashboard 요약 데이터 반환 테스트"""
        dashboard = PerformanceDashboard()
        
        sample_data = {
            'total_return': 15.5,
            'sharpe_ratio': 1.85,
            'max_drawdown': -8.5,
            'win_rate': 65.2
        }
        
        dashboard.update_performance_data(sample_data)
        summary = dashboard.get_summary_data()
        
        assert 'total_return' in summary
        assert 'sharpe_ratio' in summary
        assert 'max_drawdown' in summary
        assert 'win_rate' in summary
        assert 'timestamp' in summary
    
    def test_dashboard_color_coding(self, qapp):
        """PerformanceDashboard 색상 코딩 테스트"""
        dashboard = PerformanceDashboard()
        
        # 좋은 성과 (녹색)
        good_data = {
            'total_return': 15.5,
            'sharpe_ratio': 2.0,
            'max_drawdown': -3.0
        }
        dashboard.update_performance_data(good_data)
        
        return_color = dashboard.total_return_card.value_label.styleSheet()
        sharpe_color = dashboard.sharpe_ratio_card.value_label.styleSheet()
        drawdown_color = dashboard.max_drawdown_card.value_label.styleSheet()
        
        assert "#4CAF50" in return_color  # 녹색
        assert "#4CAF50" in sharpe_color  # 녹색
        assert "#4CAF50" in drawdown_color  # 녹색
        
        # 나쁜 성과 (빨간색)
        bad_data = {
            'total_return': -10.5,
            'sharpe_ratio': 0.3,
            'max_drawdown': -20.0
        }
        dashboard.update_performance_data(bad_data)
        
        return_color = dashboard.total_return_card.value_label.styleSheet()
        sharpe_color = dashboard.sharpe_ratio_card.value_label.styleSheet()
        drawdown_color = dashboard.max_drawdown_card.value_label.styleSheet()
        
        assert "#FF4444" in return_color  # 빨간색
        assert "#FF4444" in sharpe_color  # 빨간색
        assert "#FF4444" in drawdown_color  # 빨간색
    
    def test_dashboard_signal_emission(self, qapp):
        """PerformanceDashboard 시그널 방출 테스트"""
        dashboard = PerformanceDashboard()
        
        # 시그널 연결 테스트
        refresh_called = False
        export_called = False
        
        def on_refresh():
            nonlocal refresh_called
            refresh_called = True
        
        def on_export():
            nonlocal export_called
            export_called = True
        
        dashboard.refresh_requested.connect(on_refresh)
        dashboard.export_requested.connect(on_export)
        
        # 시그널 방출
        dashboard.refresh_requested.emit()
        dashboard.export_requested.emit()
        
        assert refresh_called
        assert export_called