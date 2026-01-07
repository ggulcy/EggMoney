"""Order Repository Interface"""
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from domain.entities.order import Order


class OrderRepository(ABC):
    """TWAP 주문 저장소 인터페이스"""

    @abstractmethod
    def save(self, order: Order) -> None:
        """주문 저장 (생성 또는 업데이트)"""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Order]:
        """name으로 주문 조회"""
        pass

    @abstractmethod
    def find_all(self) -> List[Order]:
        """전체 주문 조회 (name 오름차순)"""
        pass

    @abstractmethod
    def delete_by_name(self, name: str) -> None:
        """name으로 주문 삭제"""
        pass

    @abstractmethod
    def delete_orders(self, orders: List[Order]) -> int:
        """주문 목록 삭제 (삭제된 개수 반환)"""
        pass

    @abstractmethod
    def find_old_orders(self, before_date: date) -> List[Order]:
        """특정 날짜 이전의 모든 주문 조회"""
        pass

    @abstractmethod
    def delete_old_orders(self, before_date: date) -> int:
        """특정 날짜 이전의 모든 주문 삭제 (삭제된 개수 반환)"""
        pass

    @abstractmethod
    def has_sell_order_today(self, name: str) -> bool:
        """오늘 생성된 매도 주문이 있는지 확인"""
        pass

    @abstractmethod
    def remove_trade_result(self, name: str, trade_result: Dict[str, Any]) -> bool:
        """특정 주문의 trade_result_list에서 거래 결과 제거 (성공 시 True)"""
        pass

    @abstractmethod
    def find_all_by_symbol(self, symbol: str) -> List[Order]:
        """
        같은 symbol의 모든 Order 조회

        Args:
            symbol: 종목 심볼 (예: "TQQQ")

        Returns:
            해당 symbol의 Order 리스트
        """
        pass
