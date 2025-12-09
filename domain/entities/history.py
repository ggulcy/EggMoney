"""History Entity - 거래 이력"""
from datetime import datetime
from domain.value_objects.trade_type import TradeType


class History:
    """거래 이력 엔티티"""

    def __init__(
        self,
        date_added: datetime,
        trade_date: datetime,
        trade_type: TradeType,
        name: str,
        symbol: str,
        buy_price: float,
        sell_price: float,
        amount: float,
        profit: float,
        profit_rate: float
    ):
        # 복합 PK 검증
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if not isinstance(date_added, datetime):
            raise ValueError("date_added must be a datetime object")
        if not isinstance(trade_date, datetime):
            raise ValueError("trade_date must be a datetime object")
        if not isinstance(trade_type, TradeType):
            raise ValueError("trade_type must be a TradeType enum")

        # 가격 검증
        if buy_price < 0:
            raise ValueError("buy_price cannot be negative")
        if sell_price < 0:
            raise ValueError("sell_price cannot be negative")
        if amount < 0:
            raise ValueError("amount cannot be negative")

        self.date_added = date_added
        self.trade_date = trade_date
        self.trade_type = trade_type
        self.name = name.strip()
        self.symbol = symbol.strip().upper()
        self.buy_price = round(float(buy_price), 2)
        self.sell_price = round(float(sell_price), 2)
        self.amount = float(amount)
        self.profit = round(float(profit), 2)
        self.profit_rate = round(float(profit_rate), 2)

    def get_profit_dollar(self) -> str:
        """수익금을 달러 형식으로 반환"""
        return f"${self.profit:,.2f}"

    def get_profit_rate_percent(self) -> str:
        """수익률을 퍼센트 형식으로 반환 (0.1 → 10%)"""
        return f"{self.profit_rate * 100:.2f}%"

    def is_profitable(self) -> bool:
        """수익이 났는지 확인"""
        return self.profit > 0

    def __repr__(self):
        return (f"<History(date_added={self.date_added}, trade_date={self.trade_date}, "
                f"trade_type={self.trade_type.value}, name={self.name}, symbol={self.symbol}, "
                f"buy_price=${self.buy_price:.2f}, sell_price=${self.sell_price:.2f}, "
                f"amount={self.amount}, profit=${self.profit:.2f}, profit_rate={self.get_profit_rate_percent()})>")

    def __str__(self):
        return self.__repr__()
