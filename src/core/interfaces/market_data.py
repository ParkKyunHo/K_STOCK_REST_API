"""
시장 데이터 제공자 인터페이스
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


class IMarketDataProvider(ABC):
    """시장 데이터 제공자 인터페이스"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        데이터 소스에 연결
        
        Returns:
            연결 성공 여부
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """데이터 소스 연결 해제"""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str], data_type: str = "quote") -> bool:
        """
        실시간 데이터 구독
        
        Args:
            symbols: 구독할 종목 코드 리스트
            data_type: 데이터 타입 (quote, orderbook, trade 등)
            
        Returns:
            구독 성공 여부
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        실시간 데이터 구독 해제
        
        Args:
            symbols: 구독 해제할 종목 코드 리스트
            
        Returns:
            구독 해제 성공 여부
        """
        pass
    
    @abstractmethod
    async def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        최신 데이터 조회
        
        Args:
            symbol: 종목 코드
            
        Returns:
            최신 시장 데이터 또는 None
        """
        pass
    
    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        과거 데이터 조회
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 데이터 간격 (1m, 5m, 15m, 30m, 60m, 1d, 1w, 1M)
            
        Returns:
            OHLCV 데이터프레임
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        pass