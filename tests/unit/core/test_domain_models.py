"""
도메인 모델 테스트
"""
import pytest
from datetime import datetime
from decimal import Decimal


class TestPositionModel:
    """Position 모델 테스트"""
    
    def test_position_creation(self):
        """포지션 생성 테스트"""
        from src.core.models.domain import Position
        
        position = Position(
            symbol="005930",
            quantity=100,
            average_price=70000.0
        )
        
        assert position.symbol == "005930"
        assert position.quantity == 100
        assert position.average_price == 70000.0
        assert position.cost_basis == 7000000.0
    
    def test_position_update(self):
        """포지션 업데이트 테스트"""
        from src.core.models.domain import Position
        
        position = Position(
            symbol="005930",
            quantity=100,
            average_price=70000.0
        )
        
        # 추가 매수
        position.add_quantity(50, 72000.0)
        
        assert position.quantity == 150
        # 평균 단가: (100 * 70000 + 50 * 72000) / 150 = 70666.67
        assert position.average_price == pytest.approx(70666.67, 0.01)
        assert position.cost_basis == pytest.approx(10600000.0, 0.01)
    
    def test_position_pnl_calculation(self):
        """포지션 손익 계산 테스트"""
        from src.core.models.domain import Position
        
        position = Position(
            symbol="005930",
            quantity=100,
            average_price=70000.0
        )
        
        # 현재가 설정
        pnl = position.calculate_pnl(current_price=73500.0)
        
        assert pnl["unrealized_pnl"] == 350000.0
        assert pnl["unrealized_pnl_percent"] == 5.0
        assert pnl["market_value"] == 7350000.0
    
    def test_position_partial_close(self):
        """포지션 부분 청산 테스트"""
        from src.core.models.domain import Position
        
        position = Position(
            symbol="005930",
            quantity=100,
            average_price=70000.0
        )
        
        # 50주 매도
        realized_pnl = position.reduce_quantity(50, 73500.0)
        
        assert position.quantity == 50
        assert position.average_price == 70000.0  # 평균가는 변하지 않음
        assert realized_pnl == 175000.0  # 50 * (73500 - 70000)


class TestTransactionModel:
    """Transaction 모델 테스트"""
    
    def test_transaction_creation(self):
        """거래 생성 테스트"""
        from src.core.models.domain import Transaction, TransactionType
        
        transaction = Transaction(
            symbol="005930",
            transaction_type=TransactionType.BUY,
            quantity=100,
            price=70000.0,
            commission=105.0
        )
        
        assert transaction.symbol == "005930"
        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.quantity == 100
        assert transaction.price == 70000.0
        assert transaction.amount == 7000000.0
        assert transaction.commission == 105.0
        assert transaction.net_amount == 7000105.0
    
    def test_transaction_sell(self):
        """매도 거래 테스트"""
        from src.core.models.domain import Transaction, TransactionType
        
        transaction = Transaction(
            symbol="000660",
            transaction_type=TransactionType.SELL,
            quantity=50,
            price=150000.0,
            commission=112.5,
            tax=7500.0  # 거래세
        )
        
        assert transaction.amount == 7500000.0
        assert transaction.net_amount == 7500000.0 - 112.5 - 7500.0
        assert transaction.net_amount == 7492387.5


class TestPortfolioModel:
    """Portfolio 모델 테스트"""
    
    def test_portfolio_creation(self):
        """포트폴리오 생성 테스트"""
        from src.core.models.domain import Portfolio
        
        portfolio = Portfolio(
            account_id="12345678",
            initial_capital=10000000.0
        )
        
        assert portfolio.account_id == "12345678"
        assert portfolio.cash == 10000000.0
        assert portfolio.initial_capital == 10000000.0
        assert len(portfolio.positions) == 0
        assert portfolio.total_value == 10000000.0
    
    def test_portfolio_add_position(self):
        """포트폴리오 포지션 추가 테스트"""
        from src.core.models.domain import Portfolio, Position
        
        portfolio = Portfolio(
            account_id="12345678",
            initial_capital=10000000.0
        )
        
        # 포지션 추가
        position = portfolio.add_position(
            symbol="005930",
            quantity=100,
            price=70000.0,
            commission=105.0
        )
        
        assert "005930" in portfolio.positions
        assert portfolio.positions["005930"] == position
        assert portfolio.cash == 10000000.0 - 7000105.0
        assert position.quantity == 100
    
    def test_portfolio_update_position(self):
        """포트폴리오 포지션 업데이트 테스트"""
        from src.core.models.domain import Portfolio
        
        portfolio = Portfolio(
            account_id="12345678",
            initial_capital=10000000.0
        )
        
        # 첫 번째 매수
        portfolio.add_position("005930", 100, 70000.0, 105.0)
        
        # 추가 매수
        position = portfolio.add_position("005930", 50, 72000.0, 52.5)
        
        assert position.quantity == 150
        assert portfolio.cash == 10000000.0 - 7000105.0 - 3600052.5
    
    def test_portfolio_close_position(self):
        """포트폴리오 포지션 청산 테스트"""
        from src.core.models.domain import Portfolio
        
        portfolio = Portfolio(
            account_id="12345678",
            initial_capital=10000000.0
        )
        
        # 포지션 생성
        portfolio.add_position("005930", 100, 70000.0, 105.0)
        
        # 전량 매도
        realized_pnl = portfolio.close_position(
            symbol="005930",
            price=73500.0,
            commission=110.25,
            tax=7350.0
        )
        
        assert "005930" not in portfolio.positions
        assert realized_pnl == 350000.0 - 105.0 - 110.25 - 7350.0
        assert portfolio.cash == pytest.approx(10342434.5, 0.01)
    
    def test_portfolio_valuation(self):
        """포트폴리오 평가 테스트"""
        from src.core.models.domain import Portfolio
        
        portfolio = Portfolio(
            account_id="12345678",
            initial_capital=10000000.0
        )
        
        # 여러 포지션 추가
        portfolio.add_position("005930", 100, 70000.0, 105.0)
        portfolio.add_position("000660", 50, 150000.0, 112.5)
        
        # 현재가 설정
        current_prices = {
            "005930": 73500.0,
            "000660": 145000.0
        }
        
        valuation = portfolio.calculate_value(current_prices)
        
        expected_value = (
            portfolio.cash +  # 현금
            100 * 73500.0 +   # 삼성전자
            50 * 145000.0     # SK하이닉스
        )
        
        assert valuation["total_value"] == pytest.approx(expected_value, 0.01)
        assert valuation["total_pnl"] == pytest.approx(100000.0, 0.01)  # 미실현 손익
        assert "positions" in valuation


class TestAccountModel:
    """Account 모델 테스트"""
    
    def test_account_creation(self):
        """계좌 생성 테스트"""
        from src.core.models.domain import Account, AccountType
        
        account = Account(
            account_id="12345678",
            account_type=AccountType.STOCK,
            name="주식계좌",
            currency="KRW"
        )
        
        assert account.account_id == "12345678"
        assert account.account_type == AccountType.STOCK
        assert account.name == "주식계좌"
        assert account.currency == "KRW"
        assert account.is_active is True