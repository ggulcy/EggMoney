"""NettingPair Value Object - 장부거래 상쇄 쌍"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.order import Order


@dataclass
class NettingPair:
    """
    장부거래 상쇄 쌍

    같은 symbol에 대해 매수/매도 주문서가 동시에 존재할 때,
    실제 API 호출 없이 내부 장부거래로 상쇄할 정보를 담는 Value Object.

    Attributes:
        buy_order: 매수 주문서
        sell_order: 매도 주문서
        netting_amount: 상쇄할 수량 (개)
        current_price: 현재가 (장부거래 단가로 사용)

    Example:
        - bot1: TQQQ 매수 30개
        - bot2: TQQQ 매도 50개
        → NettingPair(bot1_order, bot2_order, 30, 100.0)
        → bot1: +30개 장부거래, bot2: -30개 장부거래, 남은 20개 실제 매도
    """
    buy_order: 'Order'
    sell_order: 'Order'
    netting_amount: int
    current_price: float

    def __post_init__(self):
        """유효성 검증"""
        if self.netting_amount <= 0:
            raise ValueError("netting_amount must be positive")
        if self.current_price <= 0:
            raise ValueError("current_price must be positive")
        if self.buy_order.symbol != self.sell_order.symbol:
            raise ValueError("buy_order and sell_order must have the same symbol")

    @property
    def symbol(self) -> str:
        """상쇄 대상 심볼"""
        return self.buy_order.symbol

    @property
    def total_value(self) -> float:
        """상쇄 총 금액 (수량 × 현재가)"""
        return round(self.netting_amount * self.current_price, 2)

    def __repr__(self) -> str:
        return (
            f"NettingPair("
            f"buy={self.buy_order.name}, "
            f"sell={self.sell_order.name}, "
            f"symbol={self.symbol}, "
            f"amount={self.netting_amount}, "
            f"price=${self.current_price:,.2f}, "
            f"total=${self.total_value:,.2f})"
        )
