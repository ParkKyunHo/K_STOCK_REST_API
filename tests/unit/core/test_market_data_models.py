"""
시장 데이터 모델 테스트
"""
from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.core.models.market_data import (
    DataPoint,
    MarketData,
    MarketDataCollection,
    OHLCV,
    OrderBook,
    OrderBookEntry,
    Quote,
    Trade,
)


class TestMarketDataModels:
    """시장 데이터 모델 테스트"""
    
    def test_quote_creation(self):
        """현재가 데이터 생성 테스트"""
        timestamp = datetime.now()
        
        quote = Quote(
            symbol="005930",
            timestamp=timestamp,
            data_type="quote",
            source="kiwoom",
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000")
        )
        
        assert quote.symbol == "005930"
        assert quote.price == Decimal("70000")
        assert quote.data_type == "quote"
        assert quote.change_rate == Decimal("1.45")
    
    def test_quote_to_dict(self):
        """현재가 데이터 딕셔너리 변환 테스트"""
        quote = Quote(
            symbol="005930",
            timestamp=datetime(2023, 12, 1, 15, 30),
            data_type="quote",
            source="kiwoom",
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000")
        )
        
        data_dict = quote.to_dict()
        
        assert data_dict["symbol"] == "005930"
        assert data_dict["price"] == 70000.0
        assert data_dict["change_rate"] == 1.45
        assert "timestamp" in data_dict
    
    def test_ohlcv_creation(self):
        """OHLCV 데이터 생성 테스트"""
        timestamp = datetime.now()
        
        ohlcv = OHLCV(
            symbol="005930",
            timestamp=timestamp,
            data_type="ohlcv",
            source="kiwoom",
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000"),
            close_price=Decimal("70000"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            period="1D"
        )
        
        assert ohlcv.symbol == "005930"
        assert ohlcv.close_price == Decimal("70000")
        assert ohlcv.period == "1D"
        assert ohlcv.data_type == "ohlcv"
    
    def test_ohlcv_to_series(self):
        """OHLCV pandas Series 변환 테스트"""
        timestamp = datetime(2023, 12, 1)
        
        ohlcv = OHLCV(
            symbol="005930",
            timestamp=timestamp,
            data_type="ohlcv",
            source="kiwoom",
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000"),
            close_price=Decimal("70000"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            period="1D"
        )
        
        series = ohlcv.to_series()
        
        assert series.name == timestamp
        assert series["open"] == 69500.0
        assert series["high"] == 70500.0
        assert series["low"] == 69000.0
        assert series["close"] == 70000.0
        assert series["volume"] == 1000000
    
    def test_orderbook_creation(self):
        """호가 데이터 생성 테스트"""
        timestamp = datetime.now()
        
        bids = [
            OrderBookEntry(price=Decimal("69900"), quantity=100),
            OrderBookEntry(price=Decimal("69800"), quantity=200),
        ]
        
        asks = [
            OrderBookEntry(price=Decimal("70000"), quantity=150),
            OrderBookEntry(price=Decimal("70100"), quantity=250),
        ]
        
        orderbook = OrderBook(
            symbol="005930",
            timestamp=timestamp,
            data_type="orderbook",
            source="kiwoom",
            bids=bids,
            asks=asks
        )
        
        assert orderbook.symbol == "005930"
        assert orderbook.data_type == "orderbook"
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2
        
        # 최고 매수/매도 호가 확인
        assert orderbook.best_bid.price == Decimal("69900")
        assert orderbook.best_ask.price == Decimal("70000")
        
        # 스프레드 확인
        assert orderbook.spread == Decimal("100")
    
    def test_trade_creation(self):
        """체결 데이터 생성 테스트"""
        timestamp = datetime.now()
        trade_time = datetime.now()
        
        trade = Trade(
            symbol="005930",
            timestamp=timestamp,
            data_type="trade",
            source="kiwoom",
            price=Decimal("70000"),
            quantity=100,
            trade_time=trade_time,
            side="BUY"
        )
        
        assert trade.symbol == "005930"
        assert trade.data_type == "trade"
        assert trade.price == Decimal("70000")
        assert trade.side == "BUY"
    
    def test_data_point_wrapper(self):
        """DataPoint 래퍼 테스트"""
        quote = Quote(
            symbol="005930",
            timestamp=datetime.now(),
            data_type="quote",
            source="kiwoom",
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000")
        )
        
        data_point = DataPoint(quote)
        
        assert data_point.symbol == "005930"
        assert data_point.data_type == "quote"
        assert data_point.is_quote()
        assert not data_point.is_ohlcv()
        assert not data_point.is_orderbook()
        assert not data_point.is_trade()
    
    def test_market_data_collection(self):
        """MarketDataCollection 테스트"""
        collection = MarketDataCollection()
        
        # 데이터 추가
        quote1 = Quote(
            symbol="005930",
            timestamp=datetime(2023, 12, 1, 9, 30),
            data_type="quote",
            source="kiwoom",
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000")
        )
        
        quote2 = Quote(
            symbol="005930",
            timestamp=datetime(2023, 12, 1, 10, 30),
            data_type="quote",
            source="kiwoom",
            price=Decimal("70500"),
            prev_close=Decimal("69000"),
            change=Decimal("1500"),
            change_rate=Decimal("2.17"),
            volume=1200000,
            trade_value=Decimal("84000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70800"),
            low_price=Decimal("69000")
        )
        
        collection.add(DataPoint(quote1))
        collection.add(DataPoint(quote2))
        
        # 데이터 조회
        symbol_data = collection.get_symbol_data("005930")
        assert len(symbol_data) == 2
        
        latest = collection.get_latest("005930")
        assert latest.data.price == Decimal("70500")
        
        # 종목 목록
        symbols = collection.symbols()
        assert "005930" in symbols
        
        # 데이터 개수
        assert collection.count("005930") == 2
        assert collection.count() == 2
    
    def test_ohlcv_dataframe_conversion(self):
        """OHLCV DataFrame 변환 테스트"""
        collection = MarketDataCollection()
        
        # OHLCV 데이터 추가
        dates = [
            datetime(2023, 12, 1),
            datetime(2023, 12, 2),
            datetime(2023, 12, 3)
        ]
        
        for i, date in enumerate(dates):
            ohlcv = OHLCV(
                symbol="005930",
                timestamp=date,
                data_type="ohlcv",
            source="kiwoom",
                open_price=Decimal(f"{69000 + i * 100}"),
                high_price=Decimal(f"{70000 + i * 100}"),
                low_price=Decimal(f"{68500 + i * 100}"),
                close_price=Decimal(f"{69800 + i * 100}"),
                volume=1000000 + i * 100000,
                trade_value=Decimal("70000000000"),
                period="1D"
            )
            collection.add(DataPoint(ohlcv))
        
        # DataFrame 변환
        df = collection.get_ohlcv_dataframe("005930")
        
        assert len(df) == 3
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert df.index[0] == pd.Timestamp("2023-12-01")
        assert df.iloc[0]["open"] == 69000.0
        assert df.iloc[-1]["close"] == 70000.0
    
    def test_collection_clear(self):
        """컬렉션 데이터 삭제 테스트"""
        collection = MarketDataCollection()
        
        quote = Quote(
            symbol="005930",
            timestamp=datetime.now(),
            data_type="quote",
            source="kiwoom",
            price=Decimal("70000"),
            prev_close=Decimal("69000"),
            change=Decimal("1000"),
            change_rate=Decimal("1.45"),
            volume=1000000,
            trade_value=Decimal("70000000000"),
            open_price=Decimal("69500"),
            high_price=Decimal("70500"),
            low_price=Decimal("69000")
        )
        
        collection.add(DataPoint(quote))
        assert collection.count() == 1
        
        # 특정 종목 삭제
        collection.clear("005930")
        assert collection.count() == 0
        
        # 전체 삭제
        collection.add(DataPoint(quote))
        collection.clear()
        assert collection.count() == 0