"""OrderType Value Object - TWAP 주문 타입"""
from enum import Enum


class OrderType(Enum):
    """TWAP 주문 타입 (분할 매매용)"""
    SELL = 'Sell'               # 전체 매도
    SELL_1_4 = 'Sell_1_4'       # 1/4 매도
    SELL_3_4 = 'Sell_3_4'       # 3/4 매도
    SELL_PART = 'Sell_Part'     # 부분 매도
    BUY = 'Buy'                 # 일반 매수
    BUY_FORCE = 'Buy_Force'     # 강제 매수

    def is_buy(self) -> bool:
        """매수 주문인지 확인 (일반 + 강제)"""
        return self in [OrderType.BUY, OrderType.BUY_FORCE]

    def is_sell(self) -> bool:
        """매도 주문인지 확인 (전체 + 부분)"""
        return self in [OrderType.SELL, OrderType.SELL_1_4, OrderType.SELL_3_4, OrderType.SELL_PART]

    def is_partial_sell(self) -> bool:
        """부분 매도인지 확인"""
        return self in [OrderType.SELL_1_4, OrderType.SELL_3_4, OrderType.SELL_PART]

    def is_full_sell(self) -> bool:
        """전체 매도인지 확인"""
        return self == OrderType.SELL

    def is_force(self) -> bool:
        """강제 매수인지 확인"""
        return self == OrderType.BUY_FORCE

    def get_sell_ratio(self) -> float:
        """매도 비율 반환 (0.0 ~ 1.0)"""
        if self == OrderType.SELL:
            return 1.0
        elif self == OrderType.SELL_3_4:
            return 0.75
        elif self == OrderType.SELL_1_4:
            return 0.25
        elif self == OrderType.SELL_PART:
            return 0.5  # 기본값
        return 0.0

    def __str__(self):
        return self.value
