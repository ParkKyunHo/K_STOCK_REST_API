# -*- coding: utf-8 -*-
"""
전략 목록 위젯
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QAction,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtGui import QIcon


class StrategyItem(QTreeWidgetItem):
    """전략 아이템"""
    
    def __init__(self, strategy_data: Dict[str, Any]):
        """전략 아이템 초기화"""
        super().__init__()
        
        self.strategy_id = strategy_data.get("id", "")
        self.strategy_data = strategy_data
        
        # 컬럼 데이터 설정
        self.setText(0, strategy_data.get("name", "Unknown"))
        self.setText(1, strategy_data.get("version", "0.0.0"))
        self.setText(2, strategy_data.get("category", "기타"))
        
        # 툴팁 설정
        self._setup_tooltip()
        
    def _setup_tooltip(self):
        """툴팁 설정"""
        tooltip_parts = [
            f"<b>{self.strategy_data.get('name', 'Unknown')}</b>",
            f"버전: {self.strategy_data.get('version', '0.0.0')}",
        ]
        
        if description := self.strategy_data.get("description"):
            tooltip_parts.append(f"<br>{description}")
            
        if author := self.strategy_data.get("author"):
            tooltip_parts.append(f"<br>작성자: {author}")
            
        if created_at := self.strategy_data.get("created_at"):
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%Y-%m-%d")
                tooltip_parts.append(f"생성일: {date_str}")
                
        tooltip = "<br>".join(tooltip_parts)
        
        # 모든 컬럼에 툴팁 설정
        for col in range(3):
            self.setToolTip(col, tooltip)


class StrategyListWidget(QTreeWidget):
    """전략 목록 위젯"""
    
    # 시그널
    strategy_selected = pyqtSignal(dict)  # 전략 선택 시
    strategy_double_clicked = pyqtSignal(dict)  # 전략 더블클릭 시
    strategy_deleted = pyqtSignal(str)  # 전략 삭제 시
    
    def __init__(self, parent=None):
        """전략 목록 위젯 초기화"""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self._strategies: Dict[str, StrategyItem] = {}
        
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """UI 초기화"""
        # 헤더 설정
        self.setHeaderLabels(["전략명", "버전", "카테고리"])
        
        # 트리 설정
        self.setRootIsDecorated(False)  # 루트 확장 아이콘 숨김
        self.setAlternatingRowColors(True)  # 교대 행 색상
        self.setSortingEnabled(True)  # 정렬 활성화
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # 헤더 설정
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # 컨텍스트 메뉴
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
    def _connect_signals(self):
        """시그널 연결"""
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
    def load_strategies(self, strategies: List[Dict[str, Any]]):
        """전략 목록 로드"""
        self.clear()
        self._strategies.clear()
        
        for strategy in strategies:
            self.add_strategy(strategy)
            
        # 첫 번째 컬럼으로 정렬
        self.sortItems(0, Qt.AscendingOrder)
        
    def add_strategy(self, strategy_data: Dict[str, Any]):
        """전략 추가"""
        strategy_id = strategy_data.get("id")
        if not strategy_id:
            self.logger.error("Strategy ID is required")
            return
            
        # 중복 확인
        if strategy_id in self._strategies:
            self.logger.warning(f"Strategy {strategy_id} already exists")
            return
            
        # 아이템 생성 및 추가
        item = StrategyItem(strategy_data)
        self.addTopLevelItem(item)
        self._strategies[strategy_id] = item
        
        self.logger.info(f"Added strategy: {strategy_id}")
        
    def remove_strategy(self, strategy_id: str):
        """전략 제거"""
        if strategy_id not in self._strategies:
            self.logger.warning(f"Strategy {strategy_id} not found")
            return
            
        item = self._strategies[strategy_id]
        index = self.indexOfTopLevelItem(item)
        if index >= 0:
            self.takeTopLevelItem(index)
            
        del self._strategies[strategy_id]
        self.logger.info(f"Removed strategy: {strategy_id}")
        
        # 삭제 시그널 발생
        self.strategy_deleted.emit(strategy_id)
        
    def get_selected_strategy(self) -> Optional[Dict[str, Any]]:
        """선택된 전략 반환"""
        selected_items = self.selectedItems()
        if not selected_items:
            return None
            
        item = selected_items[0]
        if isinstance(item, StrategyItem):
            return item.strategy_data
            
        return None
        
    def clear_strategies(self):
        """전략 목록 초기화"""
        self.clear()
        self._strategies.clear()
        self.logger.info("Cleared all strategies")
        
    def filter_by_category(self, category: str):
        """카테고리별 필터링"""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if category == "전체" or item.text(2) == category:
                item.setHidden(False)
            else:
                item.setHidden(True)
                
    def search_strategies(self, keyword: str):
        """전략 검색"""
        keyword_lower = keyword.lower()
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            
            # 이름, 카테고리, 설명에서 검색
            name_match = keyword_lower in item.text(0).lower()
            category_match = keyword_lower in item.text(2).lower()
            
            if isinstance(item, StrategyItem):
                desc = item.strategy_data.get("description", "")
                desc_match = keyword_lower in desc.lower()
            else:
                desc_match = False
                
            # 하나라도 매치되면 표시
            if name_match or category_match or desc_match:
                item.setHidden(False)
            else:
                item.setHidden(True)
                
    def _on_selection_changed(self):
        """선택 변경 시"""
        strategy = self.get_selected_strategy()
        if strategy:
            self.strategy_selected.emit(strategy)
            
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """아이템 더블클릭 시"""
        if isinstance(item, StrategyItem):
            self.strategy_double_clicked.emit(item.strategy_data)
            
    def _show_context_menu(self, position: QPoint):
        """컨텍스트 메뉴 표시"""
        item = self.itemAt(position)
        if not item or not isinstance(item, StrategyItem):
            return
            
        menu = self._create_context_menu()
        menu.exec_(self.mapToGlobal(position))
        
    def _create_context_menu(self) -> QMenu:
        """컨텍스트 메뉴 생성"""
        menu = QMenu(self)
        
        # 전략 실행
        run_action = QAction("전략 실행", self)
        run_action.triggered.connect(self._on_run_strategy)
        menu.addAction(run_action)
        
        # 전략 설정
        config_action = QAction("전략 설정", self)
        config_action.triggered.connect(self._on_configure_strategy)
        menu.addAction(config_action)
        
        menu.addSeparator()
        
        # 전략 복제
        duplicate_action = QAction("전략 복제", self)
        duplicate_action.triggered.connect(self._on_duplicate_strategy)
        menu.addAction(duplicate_action)
        
        # 전략 삭제
        delete_action = QAction("전략 삭제", self)
        delete_action.triggered.connect(self._on_delete_strategy)
        menu.addAction(delete_action)
        
        return menu
        
    def _on_run_strategy(self):
        """전략 실행"""
        strategy = self.get_selected_strategy()
        if strategy:
            self.logger.info(f"Running strategy: {strategy['id']}")
            # TODO: 전략 실행 구현
            
    def _on_configure_strategy(self):
        """전략 설정"""
        strategy = self.get_selected_strategy()
        if strategy:
            self.logger.info(f"Configuring strategy: {strategy['id']}")
            # TODO: 전략 설정 다이얼로그 표시
            
    def _on_duplicate_strategy(self):
        """전략 복제"""
        strategy = self.get_selected_strategy()
        if strategy:
            self.logger.info(f"Duplicating strategy: {strategy['id']}")
            # TODO: 전략 복제 구현
            
    def _on_delete_strategy(self):
        """전략 삭제"""
        strategy = self.get_selected_strategy()
        if strategy:
            self.remove_strategy(strategy['id'])
            
    def get_all_categories(self) -> List[str]:
        """모든 카테고리 반환"""
        categories = set()
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            categories.add(item.text(2))
            
        return sorted(list(categories))
        
    def refresh(self):
        """목록 새로고침"""
        # 현재 선택 저장
        current_selection = self.get_selected_strategy()
        current_id = current_selection.get("id") if current_selection else None
        
        # 정렬 상태 저장
        sort_column = self.sortColumn()
        sort_order = self.header().sortIndicatorOrder()
        
        # 다시 정렬
        self.sortItems(sort_column, sort_order)
        
        # 선택 복원
        if current_id and current_id in self._strategies:
            item = self._strategies[current_id]
            self.setCurrentItem(item)