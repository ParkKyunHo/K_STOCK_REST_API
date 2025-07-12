"""
리스크 관리자 인터페이스 테스트
"""
import pytest
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MockPosition:
    """테스트용 포지션"""
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0


@dataclass
class MockPortfolio:
    """테스트용 포트폴리오"""
    cash: float
    positions: Dict[str, MockPosition]
    total_value: float
    
    def get_position(self, symbol: str) -> Optional[MockPosition]:
        return self.positions.get(symbol)


class MockRiskManager:
    """IRiskManager 테스트를 위한 Mock 구현체"""
    
    def __init__(self, config: Dict[str, float]):
        self.config = config
        self.risk_metrics = {}
    
    def calculate_position_risk(self, position: MockPosition) -> Dict[str, float]:
        """포지션 리스크 계산"""
        position_value = position.quantity * position.current_price
        position_pnl_percent = (position.unrealized_pnl / (position.quantity * position.average_price)) * 100
        
        return {
            "position_value": position_value,
            "position_weight": 0.0,  # 포트폴리오 없이는 계산 불가
            "unrealized_pnl": position.unrealized_pnl,
            "pnl_percent": position_pnl_percent,
            "var_95": position_value * 0.02,  # 간단한 VaR 추정
            "max_loss": position_value * self.config.get("max_loss_per_position", 0.1)
        }
    
    def calculate_portfolio_risk(self, portfolio: MockPortfolio) -> Dict[str, float]:
        """포트폴리오 리스크 계산"""
        total_position_value = sum(
            pos.market_value for pos in portfolio.positions.values()
        )
        
        # 포지션 가중치 계산
        position_weights = {}
        for symbol, pos in portfolio.positions.items():
            position_weights[symbol] = pos.market_value / portfolio.total_value
        
        # 최대 포지션 비중
        max_position_weight = max(position_weights.values()) if position_weights else 0
        
        # 현금 비중
        cash_weight = portfolio.cash / portfolio.total_value
        
        return {
            "total_value": portfolio.total_value,
            "position_value": total_position_value,
            "cash_weight": cash_weight,
            "max_position_weight": max_position_weight,
            "number_of_positions": len(portfolio.positions),
            "portfolio_var_95": portfolio.total_value * 0.03  # 간단한 VaR 추정
        }
    
    def check_order_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        portfolio: MockPortfolio
    ) -> Dict[str, bool]:
        """주문 리스크 체크"""
        order_value = quantity * price
        
        # 현재 포지션
        current_position = portfolio.get_position(symbol)
        
        # 주문 후 예상 포지션
        if side == "buy":
            new_quantity = (current_position.quantity if current_position else 0) + quantity
            required_cash = order_value
        else:  # sell
            new_quantity = (current_position.quantity if current_position else 0) - quantity
            required_cash = 0
        
        # 리스크 체크
        checks = {
            "sufficient_cash": portfolio.cash >= required_cash,
            "position_limit": abs(new_quantity * price) <= portfolio.total_value * self.config.get("max_position_size", 0.2),
            "total_exposure": (portfolio.total_value - portfolio.cash + order_value) <= portfolio.total_value * self.config.get("max_total_exposure", 0.95),
            "min_cash_buffer": (portfolio.cash - required_cash) >= portfolio.total_value * self.config.get("min_cash_buffer", 0.05)
        }
        
        return checks
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        stop_loss: float,
        portfolio: MockPortfolio
    ) -> int:
        """리스크 기반 포지션 크기 계산"""
        # 리스크 금액 (포트폴리오의 일정 비율)
        risk_amount = portfolio.total_value * self.config.get("risk_per_trade", 0.02)
        
        # 주당 리스크
        risk_per_share = abs(price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        # 포지션 크기
        position_size = int(risk_amount / risk_per_share)
        
        # 최대 포지션 크기 제한
        max_position_value = portfolio.total_value * self.config.get("max_position_size", 0.2)
        max_shares = int(max_position_value / price)
        
        return min(position_size, max_shares)
    
    def get_risk_limits(self) -> Dict[str, float]:
        """리스크 한도 조회"""
        return {
            "max_position_size": self.config.get("max_position_size", 0.2),
            "max_total_exposure": self.config.get("max_total_exposure", 0.95),
            "max_loss_per_position": self.config.get("max_loss_per_position", 0.1),
            "max_daily_loss": self.config.get("max_daily_loss", 0.05),
            "max_drawdown": self.config.get("max_drawdown", 0.2),
            "risk_per_trade": self.config.get("risk_per_trade", 0.02),
            "min_cash_buffer": self.config.get("min_cash_buffer", 0.05)
        }
    
    def update_risk_limits(self, limits: Dict[str, float]) -> bool:
        """리스크 한도 업데이트"""
        for key, value in limits.items():
            if key in self.config:
                self.config[key] = value
        return True


class TestIRiskManagerInterface:
    """IRiskManager 인터페이스 테스트"""
    
    def test_risk_manager_initialization(self):
        """리스크 매니저 초기화 테스트"""
        config = {
            "max_position_size": 0.2,
            "max_total_exposure": 0.95,
            "risk_per_trade": 0.02
        }
        
        manager = MockRiskManager(config)
        assert manager.config == config
    
    def test_position_risk_calculation(self):
        """포지션 리스크 계산 테스트"""
        manager = MockRiskManager({"max_loss_per_position": 0.1})
        
        position = MockPosition(
            symbol="005930",
            quantity=100,
            average_price=70000,
            current_price=73500,
            market_value=7350000,
            unrealized_pnl=350000
        )
        
        risk = manager.calculate_position_risk(position)
        
        assert risk["position_value"] == 7350000
        assert risk["unrealized_pnl"] == 350000
        assert risk["pnl_percent"] == 5.0
        assert "var_95" in risk
        assert "max_loss" in risk
    
    def test_portfolio_risk_calculation(self):
        """포트폴리오 리스크 계산 테스트"""
        manager = MockRiskManager({})
        
        positions = {
            "005930": MockPosition("005930", 100, 70000, 73500, 7350000, 350000),
            "000660": MockPosition("000660", 50, 150000, 145000, 7250000, -250000)
        }
        
        portfolio = MockPortfolio(
            cash=5000000,
            positions=positions,
            total_value=19600000
        )
        
        risk = manager.calculate_portfolio_risk(portfolio)
        
        assert risk["total_value"] == 19600000
        assert risk["position_value"] == 14600000
        assert risk["cash_weight"] == pytest.approx(0.255, 0.001)
        assert risk["number_of_positions"] == 2
        assert "portfolio_var_95" in risk
    
    def test_order_risk_check(self):
        """주문 리스크 체크 테스트"""
        config = {
            "max_position_size": 0.2,
            "max_total_exposure": 0.95,
            "min_cash_buffer": 0.05
        }
        manager = MockRiskManager(config)
        
        portfolio = MockPortfolio(
            cash=5000000,
            positions={},
            total_value=10000000
        )
        
        # 정상 주문
        checks = manager.check_order_risk(
            symbol="005930",
            quantity=100,
            price=70000,
            side="buy",
            portfolio=portfolio
        )
        
        assert checks["sufficient_cash"] is False  # 7백만원 필요, 5백만원 보유
        assert checks["position_limit"] is False   # 70% > 20% 한도
        
        # 작은 주문
        checks2 = manager.check_order_risk(
            symbol="005930",
            quantity=20,
            price=70000,
            side="buy",
            portfolio=portfolio
        )
        
        assert checks2["sufficient_cash"] is True
        assert checks2["position_limit"] is True
    
    def test_position_sizing(self):
        """포지션 크기 계산 테스트"""
        config = {
            "risk_per_trade": 0.02,
            "max_position_size": 0.2
        }
        manager = MockRiskManager(config)
        
        portfolio = MockPortfolio(
            cash=5000000,
            positions={},
            total_value=10000000
        )
        
        # 2% 리스크, 5% 손절
        position_size = manager.calculate_position_size(
            symbol="005930",
            price=70000,
            stop_loss=66500,  # 5% 손절
            portfolio=portfolio
        )
        
        # 리스크 금액: 10,000,000 * 0.02 = 200,000
        # 주당 리스크: 70,000 - 66,500 = 3,500
        # 포지션 크기: 200,000 / 3,500 = 57.14 -> 57주
        assert position_size == 57
    
    def test_risk_limits_management(self):
        """리스크 한도 관리 테스트"""
        initial_config = {
            "max_position_size": 0.2,
            "max_total_exposure": 0.95,
            "risk_per_trade": 0.02
        }
        manager = MockRiskManager(initial_config)
        
        # 한도 조회
        limits = manager.get_risk_limits()
        assert limits["max_position_size"] == 0.2
        assert limits["risk_per_trade"] == 0.02
        
        # 한도 업데이트
        new_limits = {
            "max_position_size": 0.15,
            "risk_per_trade": 0.015
        }
        result = manager.update_risk_limits(new_limits)
        assert result is True
        
        # 업데이트 확인
        updated_limits = manager.get_risk_limits()
        assert updated_limits["max_position_size"] == 0.15
        assert updated_limits["risk_per_trade"] == 0.015