"""Order Entity - TWAP 주문"""
from datetime import datetime
from typing import List, Dict, Any
from domain.value_objects.order_type import OrderType


class Order:
    """TWAP (Time-Weighted Average Price) 주문 엔티티"""

    def __init__(
        self,
        name: str,
        date_added: datetime,
        symbol: str,
        trade_result_list: List[Dict[str, Any]],
        order_type: OrderType,
        trade_count: int,
        total_count: int,
        remain_value: float,
        total_value: float
    ):
        # 필수 필드 검증
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if not isinstance(date_added, datetime):
            raise ValueError("date_added must be a datetime object")
        if not isinstance(order_type, OrderType):
            raise ValueError("order_type must be an OrderType enum")
        if not isinstance(trade_result_list, list):
            raise ValueError("trade_result_list must be a list")

        # 숫자 검증
        if trade_count < 0:
            raise ValueError("trade_count cannot be negative")
        if total_count <= 0:
            raise ValueError("total_count must be positive")
        if trade_count > total_count:
            raise ValueError("trade_count cannot exceed total_count")
        if remain_value < 0:
            raise ValueError("remain_value cannot be negative")
        if total_value < 0:
            raise ValueError("total_value cannot be negative")

        self.name = name.strip()
        self.date_added = date_added
        self.symbol = symbol.strip().upper()
        self.trade_result_list = trade_result_list.copy()  # 리스트 복사
        self.order_type = order_type
        self.trade_count = int(trade_count)
        self.total_count = int(total_count)
        self.remain_value = round(float(remain_value), 2)
        self.total_value = round(float(total_value), 2)

    def is_completed(self) -> bool:
        """주문이 완료되었는지 확인"""
        return self.trade_count >= self.total_count

    def get_completion_rate(self) -> float:
        """완료율 반환 (0.0 ~ 1.0)"""
        if self.total_count == 0:
            return 0.0
        return self.trade_count / self.total_count

    def get_completion_percent(self) -> str:
        """완료율을 퍼센트 문자열로 반환"""
        return f"{self.get_completion_rate() * 100:.1f}%"

    def add_trade_result(self, trade_result: Dict[str, Any]) -> None:
        """거래 결과 추가 (Entity 상태 변경만, DB 커밋은 Repository에서)"""
        if not isinstance(trade_result, dict):
            raise ValueError("trade_result must be a dictionary")
        self.trade_result_list.append(trade_result)

    def remove_trade_result(self, trade_result: Dict[str, Any]) -> bool:
        """거래 결과 제거 (성공 시 True 반환)"""
        if trade_result in self.trade_result_list:
            self.trade_result_list.remove(trade_result)
            return True
        return False

    def increment_trade_count(self) -> None:
        """거래 횟수 증가"""
        if self.trade_count < self.total_count:
            self.trade_count += 1

    def update_remain_value(self, value: float) -> None:
        """남은 금액 업데이트"""
        if value < 0:
            raise ValueError("remain_value cannot be negative")
        self.remain_value = round(float(value), 2)

    def is_sell_order(self) -> bool:
        """매도 주문인지 확인"""
        return self.order_type.is_sell()

    def is_buy_order(self) -> bool:
        """매수 주문인지 확인"""
        return self.order_type.is_buy()

    def __repr__(self):
        trade_results_str = ""
        if self.trade_result_list:
            trade_results_str = "\n    ".join([str(tr) for tr in self.trade_result_list])
            trade_results_str = f"\n    {trade_results_str}"
        else:
            trade_results_str = "[]"

        return (
            f"<Order(\n"
            f"  date_added={self.date_added},\n"
            f"  name={self.name},\n"
            f"  symbol={self.symbol},\n"
            f"  order_type={self.order_type.value},\n"
            f"  trade_count={self.trade_count}/{self.total_count} ({self.get_completion_percent()}),\n"
            f"  remain_value=${self.remain_value:,.2f},\n"
            f"  total_value=${self.total_value:,.2f},\n"
            f"  trade_result_list={trade_results_str}\n"
            f")>"
        )

    def __str__(self):
        return self.__repr__()
