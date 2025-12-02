"""TradeResult Value Object - 거래 결과"""
from typing import Optional
from domain.value_objects.trade_type import TradeType


class TradeResult:
    """
    거래 결과 값 객체

    한투 API나 거래 모듈에서 반환하는 거래 결과를 표현
    """

    def __init__(
        self,
        trade_type: Optional[TradeType] = None,
        amount: Optional[float] = None,
        unit_price: Optional[float] = None,
        total_price: Optional[float] = None
    ):
        self.trade_type = trade_type
        self.amount = float(amount) if amount is not None else 0.0
        self.unit_price = round(float(unit_price), 2) if unit_price is not None else None
        self.total_price = round(float(total_price), 2) if total_price is not None else None

    def is_valid(self) -> bool:
        """거래 결과 유효성 검증"""
        return (
            self.trade_type is not None and
            self.amount > 0 and
            self.unit_price is not None and
            self.unit_price > 0 and
            self.total_price is not None and
            self.total_price > 0
        )

    def __repr__(self):
        return (
            f"TradeResult(trade_type={self.trade_type}, amount={self.amount}, "
            f"unit_price={self.unit_price}, total_price={self.total_price})"
        )
