# -*- coding: utf-8 -*-
"""
전략 목록 위젯 테스트
"""
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QMenu

from src.presentation.ui.widgets.strategy_list import StrategyListWidget, StrategyItem


@pytest.fixture
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_strategies():
    """샘플 전략 데이터"""
    return [
        {
            "id": "ma_crossover",
            "name": "이동평균 크로스오버",
            "version": "1.0.0",
            "description": "단기/장기 이동평균 교차 전략",
            "category": "추세추종",
            "author": "System",
            "created_at": datetime(2025, 1, 1),
            "parameters": {
                "short_period": 20,
                "long_period": 50
            }
        },
        {
            "id": "rsi_strategy",
            "name": "RSI 전략",
            "version": "1.1.0",
            "description": "RSI 과매수/과매도 전략",
            "category": "모멘텀",
            "author": "User",
            "created_at": datetime(2025, 1, 5),
            "parameters": {
                "period": 14,
                "overbought": 70,
                "oversold": 30
            }
        }
    ]


class TestStrategyItem:
    """전략 아이템 테스트"""
    
    def test_strategy_item_creation(self, qapp):
        """전략 아이템 생성 테스트"""
        strategy_data = {
            "id": "test_strategy",
            "name": "테스트 전략",
            "version": "1.0.0",
            "description": "테스트용 전략",
            "category": "테스트"
        }
        
        item = StrategyItem(strategy_data)
        
        # 기본 속성 확인
        assert item.strategy_id == "test_strategy"
        assert item.strategy_data == strategy_data
        assert item.text(0) == "테스트 전략"
        assert item.text(1) == "1.0.0"
        assert item.text(2) == "테스트"
        
    def test_strategy_item_tooltip(self, qapp):
        """전략 아이템 툴팁 테스트"""
        strategy_data = {
            "id": "test_strategy",
            "name": "테스트 전략",
            "version": "1.0.0",
            "description": "이것은 테스트용 전략입니다",
            "category": "테스트",
            "author": "Tester",
            "created_at": datetime(2025, 1, 10)
        }
        
        item = StrategyItem(strategy_data)
        
        # 툴팁 확인
        tooltip = item.toolTip(0)
        assert "테스트 전략" in tooltip
        assert "이것은 테스트용 전략입니다" in tooltip
        assert "작성자: Tester" in tooltip


class TestStrategyListWidget:
    """전략 목록 위젯 테스트"""
    
    def test_widget_initialization(self, qapp):
        """위젯 초기화 테스트"""
        widget = StrategyListWidget()
        
        # 기본 속성 확인
        assert isinstance(widget, QTreeWidget)
        assert widget.columnCount() == 3
        assert widget.headerItem().text(0) == "전략명"
        assert widget.headerItem().text(1) == "버전"
        assert widget.headerItem().text(2) == "카테고리"
        
        # 설정 확인
        assert widget.isHeaderHidden() is False
        assert widget.rootIsDecorated() is False
        assert widget.isSortingEnabled() is True
        
    def test_load_strategies(self, qapp, sample_strategies):
        """전략 로드 테스트"""
        widget = StrategyListWidget()
        
        # 전략 로드
        widget.load_strategies(sample_strategies)
        
        # 아이템 개수 확인
        assert widget.topLevelItemCount() == 2
        
        # 첫 번째 아이템 확인
        item1 = widget.topLevelItem(0)
        assert isinstance(item1, StrategyItem)
        assert item1.strategy_id == "ma_crossover"
        assert item1.text(0) == "이동평균 크로스오버"
        
        # 두 번째 아이템 확인
        item2 = widget.topLevelItem(1)
        assert item2.strategy_id == "rsi_strategy"
        assert item2.text(0) == "RSI 전략"
        
    def test_add_strategy(self, qapp):
        """전략 추가 테스트"""
        widget = StrategyListWidget()
        
        strategy = {
            "id": "new_strategy",
            "name": "새 전략",
            "version": "0.1.0",
            "category": "실험"
        }
        
        # 전략 추가
        widget.add_strategy(strategy)
        
        # 확인
        assert widget.topLevelItemCount() == 1
        item = widget.topLevelItem(0)
        assert item.strategy_id == "new_strategy"
        
    def test_remove_strategy(self, qapp, sample_strategies):
        """전략 제거 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 전략 제거
        widget.remove_strategy("ma_crossover")
        
        # 확인
        assert widget.topLevelItemCount() == 1
        remaining_item = widget.topLevelItem(0)
        assert remaining_item.strategy_id == "rsi_strategy"
        
    def test_get_selected_strategy(self, qapp, sample_strategies):
        """선택된 전략 가져오기 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 아이템 선택
        item = widget.topLevelItem(0)
        widget.setCurrentItem(item)
        
        # 선택된 전략 확인
        selected = widget.get_selected_strategy()
        assert selected is not None
        assert selected["id"] == "ma_crossover"
        
    def test_clear_strategies(self, qapp, sample_strategies):
        """전략 목록 초기화 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 초기화
        widget.clear_strategies()
        
        # 확인
        assert widget.topLevelItemCount() == 0
        
    def test_context_menu(self, qapp):
        """컨텍스트 메뉴 테스트"""
        widget = StrategyListWidget()
        
        # 컨텍스트 메뉴 정책 확인
        assert widget.contextMenuPolicy() == Qt.CustomContextMenu
        
        # 메뉴 액션 확인
        menu = widget._create_context_menu()
        assert isinstance(menu, QMenu)
        
        actions = menu.actions()
        action_texts = [action.text() for action in actions]
        assert "전략 실행" in action_texts
        assert "전략 설정" in action_texts
        assert "전략 삭제" in action_texts
        
    def test_double_click_signal(self, qapp, sample_strategies):
        """더블클릭 시그널 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 시그널 연결
        signal_received = []
        widget.strategy_double_clicked.connect(lambda s: signal_received.append(s))
        
        # 더블클릭 시뮬레이션
        item = widget.topLevelItem(0)
        widget.itemDoubleClicked.emit(item, 0)
        
        # 시그널 확인
        assert len(signal_received) == 1
        assert signal_received[0]["id"] == "ma_crossover"
        
    def test_filter_strategies(self, qapp, sample_strategies):
        """전략 필터링 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 카테고리별 필터
        widget.filter_by_category("모멘텀")
        
        # 표시된 아이템 확인
        visible_count = 0
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            if not item.isHidden():
                visible_count += 1
                assert item.text(2) == "모멘텀"
                
        assert visible_count == 1
        
    def test_sort_strategies(self, qapp, sample_strategies):
        """전략 정렬 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 이름으로 정렬
        widget.sortItems(0, Qt.AscendingOrder)
        
        # 정렬 확인
        first_item = widget.topLevelItem(0)
        second_item = widget.topLevelItem(1)
        assert first_item.text(0) < second_item.text(0)
        
    def test_search_strategies(self, qapp, sample_strategies):
        """전략 검색 테스트"""
        widget = StrategyListWidget()
        widget.load_strategies(sample_strategies)
        
        # 검색
        widget.search_strategies("RSI")
        
        # 검색 결과 확인
        visible_count = 0
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            if not item.isHidden():
                visible_count += 1
                assert "RSI" in item.text(0)
                
        assert visible_count == 1