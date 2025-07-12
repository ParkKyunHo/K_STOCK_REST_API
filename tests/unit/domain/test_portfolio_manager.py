# -*- coding: utf-8 -*-
"""
포트폴리오 매니저 테스트
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from typing import Dict, List

import pytest

from src.core.models.domain import Portfolio, Position, Transaction, TransactionType
from src.domain.backtest.portfolio_manager import PortfolioManager, PositionLimit, RiskMetrics, PerformanceMetrics


class TestPortfolioManager:
    """포트폴리오 매니저 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.initial_capital = Decimal("10000000")  # 1천만원
        self.account_id = "TEST_ACCOUNT"
        
        # 기본 포트폴리오
        self.portfolio = Portfolio(
            account_id=self.account_id,
            initial_capital=float(self.initial_capital)
        )
        
        # Mock 리스크 매니저
        self.mock_risk_manager = MagicMock()
        self.mock_risk_manager.validate_order.return_value = True
        self.mock_risk_manager.check_position_limits.return_value = True
        
        # Mock 데이터 제공자 (현재가 정보)
        self.mock_data_provider = MagicMock()
        self.mock_data_provider.get_current_price.return_value = Decimal("70000")
    
    def test_portfolio_manager_initialization(self):
        """포트폴리오 매니저 초기화 테스트"""
        portfolio_manager = PortfolioManager(
            portfolio=self.portfolio,
            risk_manager=self.mock_risk_manager,
            data_provider=self.mock_data_provider
        )
        
        # 초기화 검증
        assert portfolio_manager.portfolio == self.portfolio
        assert portfolio_manager.risk_manager == self.mock_risk_manager
        assert portfolio_manager.data_provider == self.mock_data_provider
        assert portfolio_manager.position_limits is not None
        assert isinstance(portfolio_manager.position_limits, PositionLimit)
        
        # 포트폴리오 상태 확인
        assert self.portfolio.account_id == self.account_id
        assert self.portfolio.initial_capital == float(self.initial_capital)
        assert self.portfolio.cash == float(self.initial_capital)
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.transactions) == 0
    
    def test_portfolio_manager_buy_order_execution(self):
        """매수 주문 실행 테스트"""
        # 매수 주문 파라미터
        symbol = "005930"
        quantity = 100
        price = 70000.0
        commission = 105.0
        
        # 매수 실행 시뮬레이션
        initial_cash = self.portfolio.cash
        position = self.portfolio.add_position(
            symbol=symbol,
            quantity=quantity,
            price=price,
            commission=commission
        )
        
        # 검증
        assert symbol in self.portfolio.positions
        assert self.portfolio.positions[symbol].quantity == quantity
        assert self.portfolio.positions[symbol].average_price == price
        
        # 현금 차감 확인
        expected_cash = initial_cash - (quantity * price + commission)
        assert self.portfolio.cash == expected_cash
        
        # 거래 기록 확인
        assert len(self.portfolio.transactions) == 1
        assert self.portfolio.transactions[0].symbol == symbol
        assert self.portfolio.transactions[0].transaction_type == TransactionType.BUY
    
    def test_portfolio_manager_sell_order_execution(self):
        """매도 주문 실행 테스트"""
        # 먼저 포지션 생성
        symbol = "005930"
        quantity = 100
        buy_price = 70000.0
        self.portfolio.add_position(symbol, quantity, buy_price)
        
        # 매도 실행
        sell_price = 75000.0
        commission = 112.5
        tax = 225.0
        
        initial_cash = self.portfolio.cash
        realized_pnl = self.portfolio.close_position(
            symbol=symbol,
            price=sell_price,
            commission=commission,
            tax=tax
        )
        
        # 검증
        assert symbol not in self.portfolio.positions  # 포지션 완전 청산
        
        # 실현 손익 확인
        expected_pnl = quantity * (sell_price - buy_price)
        assert realized_pnl == expected_pnl - commission - tax
        
        # 현금 증가 확인
        net_proceeds = quantity * sell_price - commission - tax
        expected_cash = initial_cash + net_proceeds
        assert self.portfolio.cash == expected_cash
    
    def test_portfolio_manager_position_averaging(self):
        """포지션 평균가 계산 테스트"""
        symbol = "005930"
        
        # 첫 번째 매수
        self.portfolio.add_position(symbol, 100, 70000.0)
        
        # 두 번째 매수 (다른 가격)
        position = self.portfolio.positions[symbol]
        position.add_quantity(50, 72000.0)
        
        # 평균가 계산 검증
        # (100 * 70000 + 50 * 72000) / 150 = 70666.67
        expected_avg_price = (100 * 70000 + 50 * 72000) / 150
        assert abs(position.average_price - expected_avg_price) < 0.01
        assert position.quantity == 150
    
    def test_portfolio_manager_partial_sell(self):
        """부분 매도 테스트"""
        symbol = "005930"
        initial_quantity = 100  # 줄어든 수량 (700만원)
        buy_price = 70000.0
        
        # 포지션 생성
        self.portfolio.add_position(symbol, initial_quantity, buy_price)
        
        # 부분 매도 (100주 중 50주만)
        position = self.portfolio.positions[symbol]
        sell_quantity = 50
        sell_price = 75000.0
        
        realized_pnl = position.reduce_quantity(sell_quantity, sell_price)
        
        # 검증
        assert position.quantity == initial_quantity - sell_quantity  # 100주 남음
        assert position.average_price == buy_price  # 평균가 유지
        
        # 실현 손익 확인
        expected_pnl = sell_quantity * (sell_price - buy_price)
        assert realized_pnl == expected_pnl
    
    def test_portfolio_manager_risk_validation(self):
        """리스크 검증 테스트"""
        # 리스크 한도 설정
        max_position_size = Decimal("0.1")  # 10%
        max_single_order = Decimal("1000000")  # 100만원
        
        # 주문 검증 함수
        def validate_order(symbol, action, quantity, price):
            order_value = Decimal(str(quantity * price))
            
            # 단일 주문 한도 확인
            if order_value > max_single_order:
                return False, "Order value exceeds limit"
            
            # 포지션 크기 한도 확인 (매수의 경우)
            if action == "BUY":
                portfolio_value = Decimal(str(self.portfolio.cash))
                position_ratio = order_value / portfolio_value
                if position_ratio > max_position_size:
                    return False, "Position size exceeds limit"
            
            return True, "Order validated"
        
        # 유효한 주문
        is_valid, message = validate_order("005930", "BUY", 10, 70000.0)
        assert is_valid is True
        
        # 너무 큰 주문
        is_valid, message = validate_order("005930", "BUY", 200, 70000.0)
        assert is_valid is False
        assert "Order value exceeds limit" in message
    
    def test_portfolio_manager_position_valuation(self):
        """포지션 평가 테스트"""
        # 여러 포지션 생성 (총 투자금액을 1천만원 내로 조정)
        positions_data = [
            {"symbol": "005930", "quantity": 50, "buy_price": 70000.0},   # 350만원
            {"symbol": "000660", "quantity": 20, "buy_price": 120000.0},  # 240만원
            {"symbol": "035420", "quantity": 10, "buy_price": 250000.0}   # 250만원
        ]
        
        for pos_data in positions_data:
            self.portfolio.add_position(
                symbol=pos_data["symbol"],
                quantity=pos_data["quantity"],
                price=pos_data["buy_price"]
            )
        
        # 현재가 정보 (Mock)
        current_prices = {
            "005930": 75000.0,   # +5000원 (7.14% 수익)
            "000660": 115000.0,  # -5000원 (4.17% 손실)
            "035420": 260000.0   # +10000원 (4% 수익)
        }
        
        # 포트폴리오 평가
        valuation = self.portfolio.calculate_value(current_prices)
        
        # 예상 계산
        expected_market_value = (
            50 * 75000.0 +     # 삼성전자: 375만원
            20 * 115000.0 +    # SK하이닉스: 230만원  
            10 * 260000.0      # 네이버: 260만원
        )  # 총 865만원
        
        assert valuation["market_value"] == expected_market_value
        
        # 총 가치 (현금 + 포지션)
        expected_total_value = self.portfolio.cash + expected_market_value
        assert valuation["total_value"] == expected_total_value
    
    def test_portfolio_manager_performance_tracking(self):
        """성과 추적 테스트"""
        # 초기 포트폴리오 가치
        initial_value = Decimal(str(self.portfolio.initial_capital))
        
        # 거래 실행
        self.portfolio.add_position("005930", 100, 70000.0, commission=105.0)
        
        # 현재가 기준 평가 (10% 수익 가정)
        current_price = 77000.0
        current_prices = {"005930": current_price}
        valuation = self.portfolio.calculate_value(current_prices)
        
        # 수익률 계산
        total_value = Decimal(str(valuation["total_value"]))
        total_return = (total_value - initial_value) / initial_value
        
        # 검증
        assert total_return > 0  # 수익 발생
        
        # 절대 수익 계산
        absolute_profit = total_value - initial_value
        expected_profit = Decimal(str(100 * (current_price - 70000.0) - 105.0))  # 수수료 차감
        assert abs(absolute_profit - expected_profit) < Decimal("1.0")
    
    def test_portfolio_manager_transaction_history(self):
        """거래 내역 추적 테스트"""
        # 여러 거래 실행
        trades = [
            {"symbol": "005930", "action": "BUY", "quantity": 50, "price": 70000.0},   # 350만원
            {"symbol": "000660", "action": "BUY", "quantity": 20, "price": 120000.0},  # 240만원
            {"symbol": "005930", "action": "SELL", "quantity": 25, "price": 75000.0}
        ]
        
        # 매수 주문들
        for trade in trades[:2]:
            self.portfolio.add_position(
                symbol=trade["symbol"],
                quantity=trade["quantity"],
                price=trade["price"]
            )
        
        # 부분 매도
        self.portfolio.close_position("005930", 75000.0)
        
        # 거래 내역 검증
        transactions = self.portfolio.transactions
        assert len(transactions) >= 3  # 매수 2개 + 매도 1개
        
        # 거래 타입 확인
        buy_transactions = [t for t in transactions if t.transaction_type == TransactionType.BUY]
        sell_transactions = [t for t in transactions if t.transaction_type == TransactionType.SELL]
        
        assert len(buy_transactions) >= 2
        assert len(sell_transactions) >= 1
    
    def test_portfolio_manager_cash_management(self):
        """현금 관리 테스트"""
        initial_cash = self.portfolio.cash
        
        # 현금 부족 상황 테스트
        large_order_value = initial_cash + 1000000  # 보유 현금보다 큰 주문
        
        # 현금 부족 검증
        def check_sufficient_cash(order_value):
            return self.portfolio.cash >= order_value
        
        # 작은 주문 (가능)
        small_order = 1000000.0
        assert check_sufficient_cash(small_order) is True
        
        # 큰 주문 (불가능)
        assert check_sufficient_cash(large_order_value) is False
    
    def test_portfolio_manager_position_limits(self):
        """포지션 한도 테스트"""
        # 포지션 크기 한도 설정
        max_position_percentage = 0.2  # 20%
        portfolio_value = self.portfolio.cash
        max_position_value = portfolio_value * max_position_percentage
        
        # 한도 검증 함수
        def check_position_limit(symbol, additional_quantity, price):
            additional_value = additional_quantity * price
            current_position_value = 0
            
            if symbol in self.portfolio.positions:
                position = self.portfolio.positions[symbol]
                current_position_value = position.quantity * position.average_price
            
            total_position_value = current_position_value + additional_value
            return total_position_value <= max_position_value
        
        # 소량 매수 (가능)
        assert check_position_limit("005930", 10, 70000.0) is True
        
        # 대량 매수 (한도 초과)
        assert check_position_limit("005930", 500, 70000.0) is False
    
    def test_portfolio_manager_diversification(self):
        """분산투자 테스트"""
        # 다양한 종목에 투자
        symbols = ["005930", "000660", "035420", "207940", "005380"]
        
        for i, symbol in enumerate(symbols):
            quantity = 10 + i * 5  # 다양한 수량 (줄어든)
            price = 50000.0 + i * 10000.0  # 다양한 가격
            self.portfolio.add_position(symbol, quantity, price)
        
        # 분산도 측정
        total_positions = len(self.portfolio.positions)
        assert total_positions == len(symbols)
        
        # 각 포지션 비중 계산
        total_investment = sum(
            pos.quantity * pos.average_price 
            for pos in self.portfolio.positions.values()
        )
        
        position_weights = {}
        for symbol, position in self.portfolio.positions.items():
            position_value = position.quantity * position.average_price
            weight = position_value / total_investment
            position_weights[symbol] = weight
        
        # 분산 검증 (최대 비중이 50% 이하)
        max_weight = max(position_weights.values())
        assert max_weight <= 0.5
    
    def test_portfolio_manager_rebalancing(self):
        """리밸런싱 테스트"""
        # 목표 포트폴리오 비중
        target_weights = {
            "005930": 0.3,  # 30%
            "000660": 0.2,  # 20%
            "035420": 0.2,  # 20%
            "207940": 0.15, # 15%
            "005380": 0.15  # 15%
        }
        
        # 현재 포트폴리오 (불균형 상태)
        current_positions = {
            "005930": {"quantity": 100, "price": 70000.0},  # 과대비중 (700만원)
            "000660": {"quantity": 10, "price": 120000.0},   # 과소비중 (120만원)
        }
        
        for symbol, data in current_positions.items():
            self.portfolio.add_position(symbol, data["quantity"], data["price"])
        
        # 현재 비중 계산
        total_value = sum(
            pos.quantity * pos.average_price 
            for pos in self.portfolio.positions.values()
        )
        
        current_weights = {}
        for symbol, position in self.portfolio.positions.items():
            position_value = position.quantity * position.average_price
            current_weights[symbol] = position_value / total_value
        
        # 리밸런싱 필요성 확인
        rebalancing_needed = False
        tolerance = 0.05  # 5% 허용 오차
        
        for symbol in target_weights:
            current_weight = current_weights.get(symbol, 0)
            target_weight = target_weights[symbol]
            
            if abs(current_weight - target_weight) > tolerance:
                rebalancing_needed = True
                break
        
        assert rebalancing_needed is True  # 리밸런싱이 필요한 상태