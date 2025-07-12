"""
리스크 관리자 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class IRiskManager(ABC):
    """리스크 관리자 인터페이스"""
    
    @abstractmethod
    def calculate_position_risk(self, position: any) -> Dict[str, float]:
        """
        포지션 리스크 계산
        
        Args:
            position: 포지션 정보
            
        Returns:
            리스크 지표 딕셔너리
            - position_value: 포지션 가치
            - position_weight: 포트폴리오 내 비중
            - unrealized_pnl: 미실현 손익
            - pnl_percent: 손익률
            - var_95: 95% VaR
            - max_loss: 최대 손실 한도
        """
        pass
    
    @abstractmethod
    def calculate_portfolio_risk(self, portfolio: any) -> Dict[str, float]:
        """
        포트폴리오 리스크 계산
        
        Args:
            portfolio: 포트폴리오 정보
            
        Returns:
            포트폴리오 리스크 지표
            - total_value: 총 가치
            - position_value: 포지션 가치
            - cash_weight: 현금 비중
            - max_position_weight: 최대 포지션 비중
            - number_of_positions: 포지션 수
            - portfolio_var_95: 포트폴리오 95% VaR
        """
        pass
    
    @abstractmethod
    def check_order_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        portfolio: any
    ) -> Dict[str, bool]:
        """
        주문 리스크 체크
        
        Args:
            symbol: 종목 코드
            quantity: 주문 수량
            price: 주문 가격
            side: 매수/매도 ("buy" or "sell")
            portfolio: 포트폴리오 정보
            
        Returns:
            리스크 체크 결과
            - sufficient_cash: 충분한 현금 보유 여부
            - position_limit: 포지션 한도 준수 여부
            - total_exposure: 총 노출 한도 준수 여부
            - min_cash_buffer: 최소 현금 버퍼 유지 여부
        """
        pass
    
    @abstractmethod
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        stop_loss: float,
        portfolio: any
    ) -> int:
        """
        리스크 기반 포지션 크기 계산
        
        Args:
            symbol: 종목 코드
            price: 현재 가격
            stop_loss: 손절 가격
            portfolio: 포트폴리오 정보
            
        Returns:
            적정 포지션 크기 (주식 수)
        """
        pass
    
    @abstractmethod
    def get_risk_limits(self) -> Dict[str, float]:
        """
        리스크 한도 조회
        
        Returns:
            리스크 한도 설정값
            - max_position_size: 최대 포지션 크기 (포트폴리오 대비 비율)
            - max_total_exposure: 최대 총 노출도
            - max_loss_per_position: 포지션당 최대 손실
            - max_daily_loss: 일일 최대 손실
            - max_drawdown: 최대 낙폭
            - risk_per_trade: 거래당 리스크
            - min_cash_buffer: 최소 현금 버퍼
        """
        pass
    
    @abstractmethod
    def update_risk_limits(self, limits: Dict[str, float]) -> bool:
        """
        리스크 한도 업데이트
        
        Args:
            limits: 업데이트할 리스크 한도
            
        Returns:
            업데이트 성공 여부
        """
        pass