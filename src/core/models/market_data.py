"""
시장 데이터 모델
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union

import pandas as pd


@dataclass
class MarketData:
    """기본 시장 데이터"""
    symbol: str
    timestamp: datetime
    data_type: str  # 'quote', 'orderbook', 'trade', 'ohlcv'
    source: str
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "data_type": self.data_type,
            "source": self.source
        }


@dataclass
class Quote(MarketData):
    """현재가 데이터"""
    price: Decimal
    prev_close: Decimal
    change: Decimal
    change_rate: Decimal
    volume: int
    trade_value: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    market_cap: Optional[Decimal] = None
    shares_outstanding: Optional[int] = None
    
    def __post_init__(self):
        if self.data_type != "quote":
            self.data_type = "quote"
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        base_dict = super().to_dict()
        base_dict.update({
            "price": float(self.price),
            "prev_close": float(self.prev_close),
            "change": float(self.change),
            "change_rate": float(self.change_rate),
            "volume": self.volume,
            "trade_value": float(self.trade_value),
            "open_price": float(self.open_price),
            "high_price": float(self.high_price),
            "low_price": float(self.low_price),
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "shares_outstanding": self.shares_outstanding
        })
        return base_dict


@dataclass
class OHLCV(MarketData):
    """OHLCV 봉 데이터"""
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    trade_value: Decimal
    
    # 추가 필드
    period: str  # '1D', '1H', '1m' etc.
    adj_close: Optional[Decimal] = None  # 수정종가
    
    def __post_init__(self):
        if self.data_type != "ohlcv":
            self.data_type = "ohlcv"
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        base_dict = super().to_dict()
        base_dict.update({
            "open": float(self.open_price),
            "high": float(self.high_price),
            "low": float(self.low_price),
            "close": float(self.close_price),
            "volume": self.volume,
            "trade_value": float(self.trade_value),
            "period": self.period,
            "adj_close": float(self.adj_close) if self.adj_close else None
        })
        return base_dict
    
    def to_series(self) -> pd.Series:
        """pandas Series 변환"""
        return pd.Series({
            "open": float(self.open_price),
            "high": float(self.high_price), 
            "low": float(self.low_price),
            "close": float(self.close_price),
            "volume": self.volume
        }, name=self.timestamp)


@dataclass
class OrderBookEntry:
    """호가 엔트리"""
    price: Decimal
    quantity: int
    order_count: Optional[int] = None


@dataclass
class OrderBook(MarketData):
    """호가 데이터"""
    bids: List[OrderBookEntry]  # 매수 호가 (높은 가격부터)
    asks: List[OrderBookEntry]  # 매도 호가 (낮은 가격부터)
    
    def __post_init__(self):
        if self.data_type != "orderbook":
            self.data_type = "orderbook"
    
    @property
    def best_bid(self) -> Optional[OrderBookEntry]:
        """최고 매수 호가"""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookEntry]:
        """최저 매도 호가"""
        return self.asks[0] if self.asks else None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """호가 스프레드"""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        base_dict = super().to_dict()
        base_dict.update({
            "bids": [
                {"price": float(bid.price), "quantity": bid.quantity, "orders": bid.order_count}
                for bid in self.bids
            ],
            "asks": [
                {"price": float(ask.price), "quantity": ask.quantity, "orders": ask.order_count}
                for ask in self.asks
            ]
        })
        return base_dict


@dataclass
class Trade(MarketData):
    """체결 데이터"""
    price: Decimal
    quantity: int
    trade_time: datetime
    side: str  # 'BUY', 'SELL', 'UNKNOWN'
    
    def __post_init__(self):
        if self.data_type != "trade":
            self.data_type = "trade"
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        base_dict = super().to_dict()
        base_dict.update({
            "price": float(self.price),
            "quantity": self.quantity,
            "trade_time": self.trade_time.isoformat(),
            "side": self.side
        })
        return base_dict


class DataPoint:
    """단일 데이터 포인트 (다양한 타입 지원)"""
    
    def __init__(self, data: Union[Quote, OHLCV, OrderBook, Trade]):
        self.data = data
    
    @property
    def symbol(self) -> str:
        return self.data.symbol
    
    @property
    def timestamp(self) -> datetime:
        return self.data.timestamp
    
    @property
    def data_type(self) -> str:
        return self.data.data_type
    
    def to_dict(self) -> Dict:
        return self.data.to_dict()
    
    def is_quote(self) -> bool:
        return isinstance(self.data, Quote)
    
    def is_ohlcv(self) -> bool:
        return isinstance(self.data, OHLCV)
    
    def is_orderbook(self) -> bool:
        return isinstance(self.data, OrderBook)
    
    def is_trade(self) -> bool:
        return isinstance(self.data, Trade)


class MarketDataCollection:
    """시장 데이터 컬렉션"""
    
    def __init__(self):
        self._data: Dict[str, List[DataPoint]] = {}
    
    def add(self, data_point: DataPoint):
        """데이터 포인트 추가"""
        symbol = data_point.symbol
        if symbol not in self._data:
            self._data[symbol] = []
        self._data[symbol].append(data_point)
    
    def get_symbol_data(self, symbol: str) -> List[DataPoint]:
        """특정 종목의 모든 데이터"""
        return self._data.get(symbol, [])
    
    def get_latest(self, symbol: str) -> Optional[DataPoint]:
        """특정 종목의 최신 데이터"""
        symbol_data = self.get_symbol_data(symbol)
        return symbol_data[-1] if symbol_data else None
    
    def get_ohlcv_dataframe(self, symbol: str) -> pd.DataFrame:
        """OHLCV 데이터를 DataFrame으로 변환"""
        symbol_data = self.get_symbol_data(symbol)
        ohlcv_data = [dp for dp in symbol_data if dp.is_ohlcv()]
        
        if not ohlcv_data:
            return pd.DataFrame()
        
        series_list = [dp.data.to_series() for dp in ohlcv_data]
        df = pd.DataFrame(series_list)
        df.index = pd.to_datetime(df.index)
        return df.sort_index()
    
    def symbols(self) -> List[str]:
        """모든 종목 코드 반환"""
        return list(self._data.keys())
    
    def count(self, symbol: str = None) -> int:
        """데이터 개수"""
        if symbol:
            return len(self.get_symbol_data(symbol))
        return sum(len(data_list) for data_list in self._data.values())
    
    def clear(self, symbol: str = None):
        """데이터 삭제"""
        if symbol:
            self._data.pop(symbol, None)
        else:
            self._data.clear()