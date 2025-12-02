"""Trade Entity - 거래 정보 엔티티"""
from datetime import datetime
from typing import Optional
from domain.value_objects.trade_type import TradeType


class Trade:
    """
    거래 정보 엔티티

    매수/매도 거래 이력을 관리하며, 리밸런싱 로직을 포함
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        purchase_price: float,
        amount: float,
        trade_type: TradeType,
        total_price: float,
        date_added: datetime,
        latest_date_trade: datetime
    ):
        self.name = name
        self.symbol = symbol
        self.purchase_price = purchase_price
        self.amount = amount
        self.trade_type = trade_type
        self.total_price = total_price
        self.date_added = date_added
        self.latest_date_trade = latest_date_trade

        self._validate()

    def _validate(self):
        """비즈니스 규칙 검증"""
        if not self.name:
            raise ValueError("name은 필수입니다")
        if not self.symbol:
            raise ValueError("symbol은 필수입니다")
        if self.purchase_price < 0:
            raise ValueError("purchase_price는 0 이상이어야 합니다")
        if self.amount < 0:
            raise ValueError("amount는 0 이상이어야 합니다")
        if self.total_price < 0:
            raise ValueError("total_price는 0 이상이어야 합니다")
        if not isinstance(self.trade_type, TradeType):
            raise ValueError("trade_type은 TradeType Enum이어야 합니다")

    def get_average_price(self) -> float:
        """평균 매수 단가 계산"""
        if self.amount == 0:
            return 0.0
        return round(self.total_price / self.amount, 2)

    def update_latest_trade_date(self):
        """최근 거래 일시 업데이트"""
        self.latest_date_trade = datetime.now()

    def rebalance_buy(self, buy_amount: float, buy_unit_price: float, buy_total_price: float):
        """
        매수 리밸런싱

        Args:
            buy_amount: 매수 수량
            buy_unit_price: 매수 단가
            buy_total_price: 매수 총액
        """
        self.amount += buy_amount
        self.total_price += buy_total_price
        self.purchase_price = round(self.total_price / self.amount, 2)
        self.latest_date_trade = datetime.now()

    def rebalance_sell(self, sell_amount: float):
        """
        매도 리밸런싱

        Args:
            sell_amount: 매도 수량
        """
        if sell_amount > self.amount:
            raise ValueError(f"매도 수량({sell_amount})이 보유 수량({self.amount})을 초과합니다")

        self.amount -= sell_amount
        self.total_price = self.amount * self.purchase_price
        self.latest_date_trade = datetime.now()

    def is_active(self) -> bool:
        """활성 거래 여부 (보유 수량 > 0)"""
        return self.amount > 0

    def __repr__(self):
        return (
            f"Trade(name={self.name}, symbol={self.symbol}, "
            f"purchase_price={self.purchase_price}, amount={self.amount}, "
            f"trade_type={self.trade_type.value})"
        )
