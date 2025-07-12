# -*- coding: utf-8 -*-
"""
포지션 크기 관리자 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from src.domain.risk.position_sizer import (
    PositionSizer,
    PositionSizingMethod,
    PositionSizeResult,
    RiskLimits
)
from src.core.models.domain import Portfolio, Position


class TestPositionSizer:
    """포지션 크기 관리자 테스트"""
    
    @pytest.fixture
    def risk_limits(self):
        """기본 리스크 한도"""
        return RiskLimits(
            max_position_weight=Decimal("0.20"),  # 20%
            max_total_exposure=Decimal("0.90"),   # 90%
            risk_per_trade=Decimal("0.02"),       # 2%
            min_cash_buffer=Decimal("0.10"),      # 10%
            max_correlation_exposure=Decimal("0.40")  # 40%
        )
    
    @pytest.fixture
    def mock_portfolio(self):
        """Mock 포트폴리오"""
        portfolio = Mock(spec=Portfolio)
        portfolio.total_value = Decimal("10000000")  # 1천만원
        portfolio.cash = Decimal("5000000")  # 500만원
        portfolio.positions = {}
        return portfolio
    
    @pytest.fixture
    def position_sizer(self, risk_limits):
        """포지션 크기 관리자"""
        return PositionSizer(risk_limits)
    
    def test_initialization(self, position_sizer, risk_limits):
        """초기화 테스트"""
        assert position_sizer.risk_limits == risk_limits
        assert position_sizer.logger is not None
    
    def test_calculate_fixed_amount_size(self, position_sizer, mock_portfolio):
        """고정 금액 방식 포지션 크기 계산"""
        result = position_sizer.calculate_position_size(
            symbol="005930",  # 삼성전자
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.FIXED_AMOUNT,
            amount=Decimal("1000000")  # 100만원
        )
        
        assert isinstance(result, PositionSizeResult)
        assert result.shares == 14  # 1,000,000 / 70,000 = 14.28... -> 14
        assert result.position_value == Decimal("980000")  # 14 * 70,000
        assert result.is_valid is True
        assert "FIXED_AMOUNT" in result.method
    
    def test_calculate_percentage_size(self, position_sizer, mock_portfolio):
        """비율 방식 포지션 크기 계산"""
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.PERCENTAGE,
            percentage=Decimal("0.15")  # 15%
        )
        
        # 15% of 10,000,000 = 1,500,000
        expected_shares = int(Decimal("1500000") / Decimal("70000"))  # 21
        assert result.shares == expected_shares
        assert result.position_value == expected_shares * Decimal("70000")
        assert result.is_valid is True
    
    def test_calculate_risk_based_size(self, position_sizer, mock_portfolio):
        """리스크 기반 포지션 크기 계산"""
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.RISK_BASED,
            stop_loss_price=Decimal("63000")  # 10% 손절
        )
        
        # 2% 리스크로 10% 손실 시 포지션 크기
        # 리스크 금액: 10,000,000 * 0.02 = 200,000
        # 주당 손실: 70,000 - 63,000 = 7,000
        # 주식 수: 200,000 / 7,000 = 28.57... -> 28
        assert result.shares == 28
        assert result.is_valid is True
        assert result.risk_amount <= Decimal("200000")
    
    def test_calculate_volatility_based_size(self, position_sizer, mock_portfolio):
        """변동성 기반 포지션 크기 계산"""
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.VOLATILITY_BASED,
            volatility=Decimal("0.25")  # 25% 연변동성
        )
        
        assert isinstance(result, PositionSizeResult)
        assert result.shares > 0
        assert result.is_valid is True
    
    def test_kelly_criterion_size(self, position_sizer, mock_portfolio):
        """켈리 기준 포지션 크기 계산"""
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.KELLY_CRITERION,
            win_probability=Decimal("0.6"),  # 60% 승률
            avg_win=Decimal("0.15"),  # 평균 수익 15%
            avg_loss=Decimal("0.10")  # 평균 손실 10%
        )
        
        assert isinstance(result, PositionSizeResult)
        assert result.shares >= 0
        assert result.is_valid is True
    
    def test_position_weight_limit_validation(self, position_sizer, mock_portfolio):
        """포지션 비중 한도 검증"""
        # 20% 한도를 초과하는 요청
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.PERCENTAGE,
            percentage=Decimal("0.25")  # 25% > 20% 한도
        )
        
        # 한도에 맞춰 조정되어야 함
        max_value = mock_portfolio.total_value * position_sizer.risk_limits.max_position_weight
        expected_shares = int(max_value / Decimal("70000"))
        assert result.shares == expected_shares
        assert result.is_valid is True
        assert "adjusted" in result.notes.lower()
    
    def test_insufficient_cash_validation(self, position_sizer, mock_portfolio):
        """현금 부족 검증"""
        # 현금보다 많은 금액 요청
        mock_portfolio.cash = Decimal("100000")  # 10만원만 보유
        
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.FIXED_AMOUNT,
            amount=Decimal("1000000")  # 100만원 요청
        )
        
        assert result.shares == 0
        assert result.is_valid is False
        assert "insufficient" in result.notes.lower()
    
    def test_min_cash_buffer_validation(self, position_sizer, mock_portfolio):
        """최소 현금 버퍼 검증"""
        # 현금 버퍼를 고려한 포지션 크기 계산
        mock_portfolio.cash = Decimal("1000000")  # 100만원 현금
        
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.FIXED_AMOUNT,
            amount=Decimal("950000")  # 95만원 요청
        )
        
        # 10% 버퍼를 고려하면 90만원까지만 사용 가능
        max_available = mock_portfolio.cash * (Decimal("1") - position_sizer.risk_limits.min_cash_buffer)
        expected_shares = int(max_available / Decimal("70000"))
        assert result.shares == expected_shares
    
    def test_correlation_limit_validation(self, position_sizer, mock_portfolio):
        """상관관계 한도 검증"""
        # 기존 포지션과 높은 상관관계를 가진 종목
        existing_position = Mock(spec=Position)
        existing_position.symbol = "000660"  # SK하이닉스 (반도체)
        existing_position.market_value = Decimal("2000000")  # 200만원
        mock_portfolio.positions = {"000660": existing_position}
        
        with patch.object(position_sizer, '_get_correlation', return_value=Decimal("0.8")):
            result = position_sizer.calculate_position_size(
                symbol="005930",  # 삼성전자 (반도체)
                current_price=Decimal("70000"),
                portfolio=mock_portfolio,
                method=PositionSizingMethod.PERCENTAGE,
                percentage=Decimal("0.30")  # 30%
            )
            
            # 상관관계 한도 초과로 조정되어야 함
            assert result.is_valid is True
            # 추가 검증 로직 필요 시 여기에 추가
    
    def test_invalid_parameters(self, position_sizer, mock_portfolio):
        """잘못된 파라미터 처리"""
        # 음수 가격
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("-1000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.FIXED_AMOUNT,
            amount=Decimal("1000000")
        )
        
        assert result.shares == 0
        assert result.is_valid is False
        assert "invalid" in result.notes.lower()
    
    def test_zero_amount_request(self, position_sizer, mock_portfolio):
        """0 금액 요청 처리"""
        result = position_sizer.calculate_position_size(
            symbol="005930",
            current_price=Decimal("70000"),
            portfolio=mock_portfolio,
            method=PositionSizingMethod.FIXED_AMOUNT,
            amount=Decimal("0")
        )
        
        assert result.shares == 0
        assert result.is_valid is True
        assert result.position_value == Decimal("0")


class TestRiskLimits:
    """리스크 한도 테스트"""
    
    def test_default_risk_limits(self):
        """기본 리스크 한도"""
        limits = RiskLimits()
        
        assert limits.max_position_weight == Decimal("0.20")
        assert limits.max_total_exposure == Decimal("0.90")
        assert limits.risk_per_trade == Decimal("0.02")
        assert limits.min_cash_buffer == Decimal("0.10")
    
    def test_custom_risk_limits(self):
        """커스텀 리스크 한도"""
        limits = RiskLimits(
            max_position_weight=Decimal("0.15"),
            risk_per_trade=Decimal("0.01")
        )
        
        assert limits.max_position_weight == Decimal("0.15")
        assert limits.risk_per_trade == Decimal("0.01")
    
    def test_risk_limits_validation(self):
        """리스크 한도 검증"""
        # 잘못된 값들
        with pytest.raises(ValueError):
            RiskLimits(max_position_weight=Decimal("1.5"))  # 150% > 100%
        
        with pytest.raises(ValueError):
            RiskLimits(risk_per_trade=Decimal("-0.01"))  # 음수
        
        with pytest.raises(ValueError):
            RiskLimits(min_cash_buffer=Decimal("1.1"))  # 110% > 100%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])