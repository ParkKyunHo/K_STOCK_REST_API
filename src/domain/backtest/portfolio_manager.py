# -*- coding: utf-8 -*-
"""
포트폴리오 매니저 구현
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from src.core.models.domain import Portfolio, Position, Transaction, TransactionType
from src.core.interfaces.risk_manager import IRiskManager
from src.core.interfaces.market_data import IMarketDataProvider


@dataclass
class PositionLimit:
    """포지션 한도 설정"""
    max_position_percentage: Decimal = Decimal("0.2")  # 20%
    max_single_order_value: Decimal = Decimal("1000000")  # 100만원
    max_concentration_risk: Decimal = Decimal("0.3")  # 30%


@dataclass
class RiskMetrics:
    """리스크 지표"""
    total_exposure: Decimal
    largest_position_pct: Decimal
    number_of_positions: int
    cash_percentage: Decimal
    concentration_risk: Decimal


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    total_return: Decimal
    absolute_profit: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    cash_balance: Decimal


class PortfolioManager:
    """포트폴리오 매니저
    
    포트폴리오의 고수준 관리 기능을 제공합니다:
    - 포지션 관리 및 추적
    - 리스크 관리 통합
    - 성과 계산 및 모니터링
    - 리밸런싱 지원
    """
    
    def __init__(
        self,
        portfolio: Portfolio,
        risk_manager: Optional[IRiskManager] = None,
        data_provider: Optional[IMarketDataProvider] = None,
        position_limits: Optional[PositionLimit] = None
    ):
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.data_provider = data_provider
        self.position_limits = position_limits or PositionLimit()
        
        # 상태 추적
        self.daily_snapshots: List[Dict[str, Any]] = []
        self.performance_history: List[PerformanceMetrics] = []
        
        # 로거
        self.logger = logging.getLogger(__name__)
        
        # 캐시된 가격 정보
        self._price_cache: Dict[str, Decimal] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 5
    
    async def execute_buy_order(
        self,
        symbol: str,
        quantity: int,
        price: Optional[Decimal] = None,
        validate_risk: bool = True
    ) -> Tuple[bool, str, Optional[Position]]:
        """매수 주문 실행
        
        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격 (None이면 현재가 사용)
            validate_risk: 리스크 검증 여부
            
        Returns:
            (성공여부, 메시지, 포지션)
        """
        try:
            # 가격 결정
            if price is None:
                price = await self._get_current_price(symbol)
                if price is None:
                    return False, f"Cannot get current price for {symbol}", None
            
            # 리스크 검증
            if validate_risk:
                is_valid, risk_message = await self._validate_buy_order(symbol, quantity, price)
                if not is_valid:
                    return False, risk_message, None
            
            # 주문 실행
            commission = self._calculate_commission(quantity, price)
            position = self.portfolio.add_position(
                symbol=symbol,
                quantity=quantity,
                price=float(price),
                commission=float(commission)
            )
            
            self.logger.info(f"Buy order executed: {symbol} x{quantity} @ {price}")
            return True, "Buy order executed successfully", position
            
        except ValueError as e:
            error_msg = f"Buy order failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected error in buy order: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    async def execute_sell_order(
        self,
        symbol: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        validate_risk: bool = True
    ) -> Tuple[bool, str, Optional[Decimal]]:
        """매도 주문 실행
        
        Args:
            symbol: 종목 코드
            quantity: 수량 (None이면 전량 매도)
            price: 가격 (None이면 현재가 사용)
            validate_risk: 리스크 검증 여부
            
        Returns:
            (성공여부, 메시지, 실현손익)
        """
        try:
            # 포지션 확인
            if symbol not in self.portfolio.positions:
                return False, f"No position found for {symbol}", None
            
            position = self.portfolio.positions[symbol]
            
            # 수량 결정
            if quantity is None:
                quantity = position.quantity
            elif quantity > position.quantity:
                return False, f"Insufficient quantity: {quantity} > {position.quantity}", None
            
            # 가격 결정
            if price is None:
                price = await self._get_current_price(symbol)
                if price is None:
                    return False, f"Cannot get current price for {symbol}", None
            
            # 리스크 검증
            if validate_risk:
                is_valid, risk_message = await self._validate_sell_order(symbol, quantity, price)
                if not is_valid:
                    return False, risk_message, None
            
            # 주문 실행
            commission = self._calculate_commission(quantity, price)
            tax = self._calculate_tax(quantity, price)
            
            if quantity == position.quantity:
                # 전량 매도
                realized_pnl = self.portfolio.close_position(
                    symbol=symbol,
                    price=float(price),
                    commission=float(commission),
                    tax=float(tax)
                )
            else:
                # 부분 매도
                realized_pnl = position.reduce_quantity(quantity, float(price))
                # 수수료, 세금 차감
                realized_pnl = realized_pnl - float(commission) - float(tax)
                
                # 현금 증가
                net_proceeds = quantity * float(price) - float(commission) - float(tax)
                self.portfolio.cash += net_proceeds
                
                # 거래 기록
                transaction = Transaction(
                    symbol=symbol,
                    transaction_type=TransactionType.SELL,
                    quantity=quantity,
                    price=float(price),
                    commission=float(commission),
                    tax=float(tax)
                )
                self.portfolio.transactions.append(transaction)
            
            self.logger.info(f"Sell order executed: {symbol} x{quantity} @ {price}, PnL: {realized_pnl}")
            return True, "Sell order executed successfully", Decimal(str(realized_pnl))
            
        except ValueError as e:
            error_msg = f"Sell order failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected error in sell order: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    async def get_portfolio_valuation(self, use_cache: bool = True) -> Dict[str, Any]:
        """포트폴리오 평가
        
        Args:
            use_cache: 가격 캐시 사용 여부
            
        Returns:
            포트폴리오 평가 결과
        """
        try:
            # 현재가 정보 수집
            current_prices = {}
            for symbol in self.portfolio.positions.keys():
                price = await self._get_current_price(symbol, use_cache)
                if price is not None:
                    current_prices[symbol] = float(price)
            
            # 포트폴리오 평가
            valuation = self.portfolio.calculate_value(current_prices)
            
            # 추가 메트릭 계산
            valuation.update({
                "total_positions": len(self.portfolio.positions),
                "total_transactions": len(self.portfolio.transactions),
                "cash_percentage": (valuation["cash"] / valuation["total_value"]) * 100 if valuation["total_value"] > 0 else 0
            })
            
            return valuation
            
        except Exception as e:
            self.logger.error(f"Portfolio valuation failed: {str(e)}")
            return {
                "total_value": self.portfolio.cash,
                "cash": self.portfolio.cash,
                "market_value": 0,
                "total_pnl": 0,
                "error": str(e)
            }
    
    async def calculate_performance_metrics(self) -> PerformanceMetrics:
        """성과 지표 계산"""
        try:
            valuation = await self.get_portfolio_valuation()
            
            total_value = Decimal(str(valuation["total_value"]))
            initial_capital = Decimal(str(self.portfolio.initial_capital))
            
            # 총 수익률
            total_return = (total_value - initial_capital) / initial_capital if initial_capital > 0 else Decimal("0")
            
            # 절대 수익
            absolute_profit = total_value - initial_capital
            
            # 실현 손익 계산
            realized_pnl = sum(
                Decimal(str(t.price * t.quantity)) - Decimal(str(t.commission or 0)) - Decimal(str(t.tax or 0))
                for t in self.portfolio.transactions
                if t.transaction_type == TransactionType.SELL
            )
            
            return PerformanceMetrics(
                total_return=total_return,
                absolute_profit=absolute_profit,
                market_value=Decimal(str(valuation.get("market_value", 0))),
                unrealized_pnl=Decimal(str(valuation.get("total_pnl", 0))),
                realized_pnl=realized_pnl,
                cash_balance=Decimal(str(self.portfolio.cash))
            )
            
        except Exception as e:
            self.logger.error(f"Performance calculation failed: {str(e)}")
            return PerformanceMetrics(
                total_return=Decimal("0"),
                absolute_profit=Decimal("0"),
                market_value=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                cash_balance=Decimal(str(self.portfolio.cash))
            )
    
    async def calculate_risk_metrics(self) -> RiskMetrics:
        """리스크 지표 계산"""
        try:
            valuation = await self.get_portfolio_valuation()
            total_value = Decimal(str(valuation["total_value"]))
            
            if total_value == 0:
                return RiskMetrics(
                    total_exposure=Decimal("0"),
                    largest_position_pct=Decimal("0"),
                    number_of_positions=0,
                    cash_percentage=Decimal("100"),
                    concentration_risk=Decimal("0")
                )
            
            # 총 노출도
            total_exposure = Decimal(str(valuation.get("market_value", 0)))
            
            # 최대 포지션 비중
            largest_position_value = Decimal("0")
            if self.portfolio.positions:
                position_values = []
                for symbol, position in self.portfolio.positions.items():
                    current_price = await self._get_current_price(symbol)
                    if current_price:
                        position_value = Decimal(str(position.quantity)) * current_price
                        position_values.append(position_value)
                
                if position_values:
                    largest_position_value = max(position_values)
            
            largest_position_pct = (largest_position_value / total_value) * 100 if total_value > 0 else Decimal("0")
            
            # 현금 비중
            cash_percentage = (Decimal(str(self.portfolio.cash)) / total_value) * 100 if total_value > 0 else Decimal("100")
            
            # 집중 리스크 (상위 3개 포지션 비중)
            concentration_risk = min(largest_position_pct, Decimal("100"))
            
            return RiskMetrics(
                total_exposure=total_exposure,
                largest_position_pct=largest_position_pct,
                number_of_positions=len(self.portfolio.positions),
                cash_percentage=cash_percentage,
                concentration_risk=concentration_risk
            )
            
        except Exception as e:
            self.logger.error(f"Risk metrics calculation failed: {str(e)}")
            return RiskMetrics(
                total_exposure=Decimal("0"),
                largest_position_pct=Decimal("0"),
                number_of_positions=0,
                cash_percentage=Decimal("100"),
                concentration_risk=Decimal("0")
            )
    
    def get_position_summary(self) -> List[Dict[str, Any]]:
        """포지션 요약 정보"""
        summary = []
        
        for symbol, position in self.portfolio.positions.items():
            position_info = {
                "symbol": symbol,
                "quantity": position.quantity,
                "average_price": position.average_price,
                "cost_basis": position.cost_basis,
                "created_at": position.created_at,
                "updated_at": position.updated_at,
                "realized_pnl": position.realized_pnl
            }
            summary.append(position_info)
        
        return summary
    
    def get_transaction_summary(self) -> Dict[str, Any]:
        """거래 요약 정보"""
        if not self.portfolio.transactions:
            return {
                "total_transactions": 0,
                "buy_count": 0,
                "sell_count": 0,
                "total_commission": 0,
                "total_tax": 0
            }
        
        buy_count = sum(1 for t in self.portfolio.transactions if t.transaction_type == TransactionType.BUY)
        sell_count = sum(1 for t in self.portfolio.transactions if t.transaction_type == TransactionType.SELL)
        total_commission = sum(t.commission for t in self.portfolio.transactions)
        total_tax = sum(t.tax for t in self.portfolio.transactions)
        
        return {
            "total_transactions": len(self.portfolio.transactions),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_commission": total_commission,
            "total_tax": total_tax,
            "first_transaction": self.portfolio.transactions[0].executed_at,
            "last_transaction": self.portfolio.transactions[-1].executed_at
        }
    
    async def _validate_buy_order(self, symbol: str, quantity: int, price: Decimal) -> Tuple[bool, str]:
        """매수 주문 검증"""
        try:
            # 주문 금액 계산
            order_value = quantity * price
            commission = self._calculate_commission(quantity, price)
            total_cost = order_value + commission
            
            # 현금 충분성 확인
            if Decimal(str(self.portfolio.cash)) < total_cost:
                return False, f"Insufficient cash: {self.portfolio.cash} < {total_cost}"
            
            # 단일 주문 한도 확인
            if total_cost > self.position_limits.max_single_order_value:
                return False, f"Order value exceeds limit: {total_cost} > {self.position_limits.max_single_order_value}"
            
            # 포지션 크기 한도 확인
            current_portfolio_value = Decimal(str(self.portfolio.cash))
            position_ratio = total_cost / current_portfolio_value
            if position_ratio > self.position_limits.max_position_percentage:
                return False, f"Position size exceeds limit: {position_ratio:.2%} > {self.position_limits.max_position_percentage:.2%}"
            
            # 외부 리스크 매니저 검증
            if self.risk_manager:
                risk_result = await self.risk_manager.validate_order(symbol, "BUY", quantity, float(price))
                if not risk_result:
                    return False, "Risk manager rejected the order"
            
            return True, "Order validated"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    async def _validate_sell_order(self, symbol: str, quantity: int, price: Decimal) -> Tuple[bool, str]:
        """매도 주문 검증"""
        try:
            # 포지션 존재 확인
            if symbol not in self.portfolio.positions:
                return False, f"No position found for {symbol}"
            
            position = self.portfolio.positions[symbol]
            
            # 수량 확인
            if quantity > position.quantity:
                return False, f"Insufficient quantity: {quantity} > {position.quantity}"
            
            # 외부 리스크 매니저 검증
            if self.risk_manager:
                risk_result = await self.risk_manager.validate_order(symbol, "SELL", quantity, float(price))
                if not risk_result:
                    return False, "Risk manager rejected the order"
            
            return True, "Order validated"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    async def _get_current_price(self, symbol: str, use_cache: bool = True) -> Optional[Decimal]:
        """현재가 조회"""
        try:
            # 캐시 확인
            if use_cache and self._is_cache_valid() and symbol in self._price_cache:
                return self._price_cache[symbol]
            
            # 데이터 제공자에서 가격 조회
            if self.data_provider:
                price = await self.data_provider.get_current_price(symbol)
                if price is not None:
                    self._update_price_cache(symbol, price)
                    return price
            
            # 폴백: 마지막 거래가 사용
            for transaction in reversed(self.portfolio.transactions):
                if transaction.symbol == symbol:
                    return Decimal(str(transaction.price))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {str(e)}")
            return None
    
    def _calculate_commission(self, quantity: int, price: Decimal) -> Decimal:
        """수수료 계산"""
        notional = quantity * price
        commission_rate = Decimal("0.0015")  # 0.15%
        return notional * commission_rate
    
    def _calculate_tax(self, quantity: int, price: Decimal) -> Decimal:
        """세금 계산 (매도시)"""
        notional = quantity * price
        tax_rate = Decimal("0.003")  # 0.3%
        return notional * tax_rate
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl_seconds
    
    def _update_price_cache(self, symbol: str, price: Decimal):
        """가격 캐시 업데이트"""
        self._price_cache[symbol] = price
        self._cache_timestamp = datetime.now()
    
    async def take_daily_snapshot(self):
        """일일 스냅샷 저장"""
        try:
            valuation = await self.get_portfolio_valuation()
            performance = await self.calculate_performance_metrics()
            risk_metrics = await self.calculate_risk_metrics()
            
            snapshot = {
                "date": datetime.now().date(),
                "valuation": valuation,
                "performance": performance,
                "risk_metrics": risk_metrics,
                "positions": self.get_position_summary(),
                "transactions_summary": self.get_transaction_summary()
            }
            
            self.daily_snapshots.append(snapshot)
            self.performance_history.append(performance)
            
            # 히스토리 크기 제한 (최근 365일)
            if len(self.daily_snapshots) > 365:
                self.daily_snapshots = self.daily_snapshots[-365:]
            
            if len(self.performance_history) > 365:
                self.performance_history = self.performance_history[-365:]
                
        except Exception as e:
            self.logger.error(f"Failed to take daily snapshot: {str(e)}")
    
    def get_portfolio(self) -> Portfolio:
        """포트폴리오 객체 반환"""
        return self.portfolio