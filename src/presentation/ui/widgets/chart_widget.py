# -*- coding: utf-8 -*-
"""
차트 위젯 (pyqtgraph 기반)
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QColor

try:
    import pyqtgraph as pg
    from pyqtgraph import DateAxisItem, ViewBox
except ImportError:
    raise ImportError("pyqtgraph가 설치되지 않았습니다. pip install pyqtgraph")


class TimeAxisItem(DateAxisItem):
    """시간축 아이템 (한국 시간 포맷)"""
    
    def tickStrings(self, values, scale, spacing):
        """눈금 문자열 생성"""
        strings = []
        
        for value in values:
            try:
                dt = datetime.fromtimestamp(value)
                
                if spacing >= 86400 * 30:  # 월 단위
                    string = dt.strftime('%Y-%m')
                elif spacing >= 86400:  # 일 단위
                    string = dt.strftime('%m/%d')
                elif spacing >= 3600:  # 시간 단위
                    string = dt.strftime('%H:%M')
                else:  # 분 단위
                    string = dt.strftime('%H:%M:%S')
                    
                strings.append(string)
            except:
                strings.append('')
                
        return strings


class CandlestickItem(pg.GraphicsObject):
    """캔들스틱 차트 아이템"""
    
    def __init__(self, data):
        """
        Args:
            data: [(time, open, high, low, close), ...] 형태의 데이터
        """
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.generatePicture()
        
    def generatePicture(self):
        """그래픽 생성"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        
        width = 0.6  # 캔들 너비
        
        for i, (t, open_, high, low, close) in enumerate(self.data):
            # 색상 결정
            if close >= open_:
                # 상승 (빨간색)
                painter.setPen(pg.mkPen('#FF0000', width=1))
                painter.setBrush(pg.mkBrush('#FF0000'))
            else:
                # 하락 (파란색)
                painter.setPen(pg.mkPen('#0000FF', width=1))
                painter.setBrush(pg.mkBrush('#0000FF'))
                
            # 고가/저가 선
            painter.drawLine(pg.QtCore.QPointF(t, low), 
                           pg.QtCore.QPointF(t, high))
            
            # 몸통
            if close != open_:
                painter.drawRect(pg.QtCore.QRectF(
                    t - width/2, min(open_, close),
                    width, abs(close - open_)
                ))
                
        painter.end()
        
    def paint(self, painter, *args):
        """페인트"""
        painter.drawPicture(0, 0, self.picture)
        
    def boundingRect(self):
        """경계 영역"""
        return pg.QtCore.QRectF(self.picture.boundingRect())


class ChartWidget(QWidget):
    """차트 위젯"""
    
    # 시그널
    time_range_changed = pyqtSignal(datetime, datetime)
    crosshair_moved = pyqtSignal(datetime, float)
    
    def __init__(self, title: str = "차트", parent=None):
        """위젯 초기화"""
        super().__init__(parent)
        self.title = title
        self._init_ui()
        self._setup_crosshair()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 툴바
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # 차트 위젯
        self.plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')}
        )
        self.plot_widget.setLabel('left', '가격')
        self.plot_widget.setLabel('bottom', '시간')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 다크 테마
        self.plot_widget.setBackground('#1e1e1e')
        
        layout.addWidget(self.plot_widget)
        
        # 정보 레이블
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.7); "
            "color: white; padding: 5px; border-radius: 3px;"
        )
        self.info_label.hide()
        
        self.setLayout(layout)
        
    def _create_toolbar(self):
        """툴바 생성"""
        toolbar = QWidget()
        toolbar.setMaximumHeight(40)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        
        # 제목
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 기간 버튼
        periods = [
            ("1D", 1),
            ("1W", 7),
            ("1M", 30),
            ("3M", 90),
            ("6M", 180),
            ("1Y", 365),
            ("전체", -1)
        ]
        
        for label, days in periods:
            btn = QPushButton(label)
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda _, d=days: self._change_period(d))
            layout.addWidget(btn)
            
        # 리셋 버튼
        reset_btn = QPushButton("리셋")
        reset_btn.clicked.connect(self.reset_view)
        layout.addWidget(reset_btn)
        
        toolbar.setLayout(layout)
        return toolbar
        
    def _setup_crosshair(self):
        """십자선 설정"""
        # 수직선
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.v_line.setPen(pg.mkPen(color='#888888', width=1, style=Qt.DashLine))
        
        # 수평선
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.h_line.setPen(pg.mkPen(color='#888888', width=1, style=Qt.DashLine))
        
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
        # 마우스 이동 이벤트
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
    def _on_mouse_moved(self, pos):
        """마우스 이동 시"""
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.getPlotItem().vb.mapSceneToView(pos)
            
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())
            
            # 시간과 가격 정보 emit
            try:
                time = datetime.fromtimestamp(mouse_point.x())
                price = mouse_point.y()
                self.crosshair_moved.emit(time, price)
                
                # 정보 레이블 업데이트
                self.info_label.setText(
                    f"{time.strftime('%Y-%m-%d %H:%M')} | {price:,.2f}"
                )
                self.info_label.move(pos.x() + 10, pos.y() - 30)
                self.info_label.show()
            except:
                pass
                
    def _change_period(self, days: int):
        """기간 변경"""
        if days == -1:
            # 전체 기간
            self.plot_widget.enableAutoRange()
        else:
            # 특정 기간
            x_range = self.plot_widget.getPlotItem().viewRange()[0]
            if x_range:
                end_time = x_range[1]
                start_time = end_time - (days * 86400)  # 초 단위
                self.plot_widget.setXRange(start_time, end_time)
                
    def plot_candlestick(self, data: List[Tuple[datetime, float, float, float, float]]):
        """캔들스틱 차트 그리기
        
        Args:
            data: [(datetime, open, high, low, close), ...] 형태의 데이터
        """
        # 시간을 timestamp로 변환
        candle_data = [
            (dt.timestamp(), open_, high, low, close)
            for dt, open_, high, low, close in data
        ]
        
        # 기존 아이템 제거
        self.plot_widget.clear()
        
        # 캔들스틱 추가
        candle_item = CandlestickItem(candle_data)
        self.plot_widget.addItem(candle_item)
        
        # 십자선 다시 추가
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
        # 뷰 조정
        self.plot_widget.enableAutoRange()
        
    def plot_line(self, 
                  data: List[Tuple[datetime, float]], 
                  name: str = "Line",
                  color: str = '#FFFFFF',
                  width: int = 2):
        """라인 차트 그리기
        
        Args:
            data: [(datetime, value), ...] 형태의 데이터
            name: 라인 이름
            color: 라인 색상
            width: 라인 너비
        """
        # 데이터 분리
        times = [dt.timestamp() for dt, _ in data]
        values = [value for _, value in data]
        
        # 라인 그리기
        pen = pg.mkPen(color=color, width=width)
        self.plot_widget.plot(times, values, pen=pen, name=name)
        
    def plot_scatter(self,
                    data: List[Tuple[datetime, float]],
                    name: str = "Points",
                    color: str = '#FFFF00',
                    size: int = 10,
                    symbol: str = 'o'):
        """산점도 그리기
        
        Args:
            data: [(datetime, value), ...] 형태의 데이터
            name: 포인트 이름
            color: 포인트 색상
            size: 포인트 크기
            symbol: 포인트 모양 ('o', 's', 't', 'd', '+')
        """
        # 데이터 분리
        times = [dt.timestamp() for dt, _ in data]
        values = [value for _, value in data]
        
        # 산점도 그리기
        self.plot_widget.plot(
            times, values,
            pen=None,
            symbol=symbol,
            symbolPen=color,
            symbolBrush=color,
            symbolSize=size,
            name=name
        )
        
    def add_horizontal_line(self, 
                           value: float,
                           color: str = '#FF0000',
                           width: int = 1,
                           style: Qt.PenStyle = Qt.DashLine):
        """수평선 추가
        
        Args:
            value: Y축 값
            color: 선 색상
            width: 선 너비
            style: 선 스타일
        """
        line = pg.InfiniteLine(
            pos=value,
            angle=0,
            pen=pg.mkPen(color=color, width=width, style=style)
        )
        self.plot_widget.addItem(line)
        
    def add_vertical_line(self,
                         time: datetime,
                         color: str = '#00FF00',
                         width: int = 1,
                         style: Qt.PenStyle = Qt.DashLine):
        """수직선 추가
        
        Args:
            time: 시간
            color: 선 색상
            width: 선 너비
            style: 선 스타일
        """
        line = pg.InfiniteLine(
            pos=time.timestamp(),
            angle=90,
            pen=pg.mkPen(color=color, width=width, style=style)
        )
        self.plot_widget.addItem(line)
        
    def add_region(self,
                  start_time: datetime,
                  end_time: datetime,
                  color: str = '#FFFF00',
                  alpha: int = 50):
        """영역 표시
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            color: 영역 색상
            alpha: 투명도 (0-255)
        """
        region = pg.LinearRegionItem(
            values=[start_time.timestamp(), end_time.timestamp()],
            brush=pg.mkBrush(*pg.colorTuple(QColor(color)), alpha),
            movable=False
        )
        self.plot_widget.addItem(region)
        
    def clear(self):
        """차트 초기화"""
        self.plot_widget.clear()
        
        # 십자선 다시 추가
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
    def reset_view(self):
        """뷰 리셋"""
        self.plot_widget.enableAutoRange()
        
    def set_y_range(self, min_val: float, max_val: float):
        """Y축 범위 설정"""
        self.plot_widget.setYRange(min_val, max_val)
        
    def set_x_range(self, start_time: datetime, end_time: datetime):
        """X축 범위 설정"""
        self.plot_widget.setXRange(
            start_time.timestamp(),
            end_time.timestamp()
        )
        
    def enable_legend(self, enable: bool = True):
        """범례 활성화"""
        if enable:
            self.plot_widget.addLegend()
        else:
            legend = self.plot_widget.getPlotItem().legend
            if legend:
                legend.scene().removeItem(legend)