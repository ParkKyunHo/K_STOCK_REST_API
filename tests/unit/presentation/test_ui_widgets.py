# -*- coding: utf-8 -*-
"""
UI 위젯 테스트
"""
import sys
import pytest
from datetime import datetime
from decimal import Decimal

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.presentation.ui.widgets.strategy_list import StrategyListWidget
from src.presentation.ui.widgets.backtest_config import BacktestConfigWidget
from src.presentation.ui.widgets.progress_widget import ProgressWidget
from src.presentation.ui.widgets.chart_widget import ChartWidget


@pytest.fixture(scope="session")
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # 세션 종료 시 정리하지 않음 (다른 테스트에서 사용 가능)


class TestStrategyListWidget:
    """전략 목록 위젯 테스트"""
    
    def test_widget_creation(self, qapp):
        """위젯 생성 테스트"""
        widget = StrategyListWidget()
        assert widget is not None
        assert widget.columnCount() == 5
        
    def test_load_strategies(self, qapp):
        """전략 로드 테스트"""
        widget = StrategyListWidget()
        
        strategies = [
            {
                "id": "test1",
                "name": "테스트 전략 1",
                "version": "1.0.0",
                "description": "설명 1",
                "category": "카테고리 1"
            },
            {
                "id": "test2",
                "name": "테스트 전략 2",
                "version": "2.0.0",
                "description": "설명 2",
                "category": "카테고리 2"
            }
        ]
        
        widget.load_strategies(strategies)
        assert widget.topLevelItemCount() == 2
        
    def test_category_grouping(self, qapp):
        """카테고리별 그룹화 테스트"""
        widget = StrategyListWidget()
        
        strategies = [
            {"id": "1", "name": "전략1", "category": "추세"},
            {"id": "2", "name": "전략2", "category": "추세"},
            {"id": "3", "name": "전략3", "category": "모멘텀"}
        ]
        
        widget.load_strategies(strategies)
        
        # 카테고리 수 확인
        category_count = 0
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            if item.data(0, Qt.UserRole) is None:  # 카테고리 아이템
                category_count += 1
                
        assert category_count == 2  # 추세, 모멘텀
        

class TestBacktestConfigWidget:
    """백테스트 설정 위젯 테스트"""
    
    def test_widget_creation(self, qapp):
        """위젯 생성 테스트"""
        widget = BacktestConfigWidget()
        assert widget is not None
        assert widget.initial_capital.text() == "10,000,000"
        
    def test_get_config(self, qapp):
        """설정 가져오기 테스트"""
        widget = BacktestConfigWidget()
        config = widget.get_config()
        
        assert "start_date" in config
        assert "end_date" in config
        assert config["initial_capital"] == Decimal("10000000")
        assert config["commission_rate"] == Decimal("0.0015")
        assert config["tax_rate"] == Decimal("0.003")
        
    def test_set_config(self, qapp):
        """설정 적용 테스트"""
        widget = BacktestConfigWidget()
        
        test_config = {
            "initial_capital": Decimal("50000000"),
            "commission_rate": Decimal("0.002"),
            "tax_rate": Decimal("0.0025"),
            "max_positions": 20
        }
        
        widget.set_config(test_config)
        
        # 값 확인
        assert widget.initial_capital.text() == "50,000,000"
        assert widget.commission_rate.value() == 0.2  # 0.002 * 100
        assert widget.tax_rate.value() == 0.25  # 0.0025 * 100
        assert widget.max_positions.value() == 20
        
    def test_validation(self, qapp):
        """설정 검증 테스트"""
        widget = BacktestConfigWidget()
        
        # 잘못된 자본금 설정
        widget.initial_capital.setText("invalid")
        assert not widget._validate_config()
        
        # 정상 자본금 복원
        widget.initial_capital.setText("10,000,000")
        assert widget._validate_config()
        

class TestProgressWidget:
    """진행률 위젯 테스트"""
    
    def test_widget_creation(self, qapp):
        """위젯 생성 테스트"""
        widget = ProgressWidget()
        assert widget is not None
        assert widget.progress_bar.value() == 0
        
    def test_start_stop(self, qapp):
        """시작/중지 테스트"""
        widget = ProgressWidget()
        
        # 시작
        widget.start()
        assert widget.pause_btn.isEnabled()
        assert widget.stop_btn.isEnabled()
        assert widget.update_timer.isActive()
        
        # 중지
        widget.stop()
        assert not widget.pause_btn.isEnabled()
        assert not widget.stop_btn.isEnabled()
        assert not widget.update_timer.isActive()
        
    def test_update_progress(self, qapp):
        """진행률 업데이트 테스트"""
        widget = ProgressWidget()
        
        widget.update_progress(0.5, "처리 중...")
        assert widget.progress_bar.value() == 50
        assert widget.stage_label.text() == "처리 중..."
        
        widget.update_progress(1.0, "완료")
        assert widget.progress_bar.value() == 100
        assert widget.stage_label.text() == "완료"
        
    def test_update_info(self, qapp):
        """정보 업데이트 테스트"""
        widget = ProgressWidget()
        
        # 거래 수 업데이트
        widget.update_trades(1234)
        assert widget.trades_label.text() == "1,234"
        
        # 포지션 수 업데이트
        widget.update_positions(5)
        assert widget.positions_label.text() == "5"
        
        # 성과 업데이트
        widget.update_performance(15.5, 11550000)
        assert widget.return_label.text() == "+15.50%"
        assert widget.equity_label.text() == "11,550,000"
        

class TestChartWidget:
    """차트 위젯 테스트"""
    
    def test_widget_creation(self, qapp):
        """위젯 생성 테스트"""
        widget = ChartWidget("테스트 차트")
        assert widget is not None
        assert widget.title == "테스트 차트"
        assert widget.plot_widget is not None
        
    def test_plot_line(self, qapp):
        """라인 차트 테스트"""
        widget = ChartWidget()
        
        # 샘플 데이터
        data = [
            (datetime(2023, 1, 1), 100),
            (datetime(2023, 1, 2), 110),
            (datetime(2023, 1, 3), 105)
        ]
        
        widget.plot_line(data, "테스트 라인", "#FF0000")
        
        # 플롯 아이템 확인
        plot_items = widget.plot_widget.getPlotItem().items
        assert len(plot_items) > 0
        
    def test_clear(self, qapp):
        """차트 초기화 테스트"""
        widget = ChartWidget()
        
        # 데이터 추가
        data = [(datetime(2023, 1, 1), 100)]
        widget.plot_line(data, "테스트")
        
        # 초기화
        widget.clear()
        
        # 십자선만 남아있는지 확인
        plot_items = widget.plot_widget.getPlotItem().items
        assert len(plot_items) == 2  # v_line, h_line만
        
    def test_add_lines(self, qapp):
        """수평선/수직선 추가 테스트"""
        widget = ChartWidget()
        
        # 수평선 추가
        widget.add_horizontal_line(100, "#FF0000")
        
        # 수직선 추가
        widget.add_vertical_line(datetime(2023, 1, 1), "#00FF00")
        
        # 아이템 수 확인 (십자선 2개 + 추가한 2개)
        plot_items = widget.plot_widget.getPlotItem().items
        assert len(plot_items) == 4