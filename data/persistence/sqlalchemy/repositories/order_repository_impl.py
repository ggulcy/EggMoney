"""Order Repository Implementation"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.entities.order import Order
from domain.repositories.order_repository import OrderRepository
from domain.value_objects.order_type import OrderType
from data.persistence.sqlalchemy.models.order_model import OrderModel


class SQLAlchemyOrderRepositoryImpl(OrderRepository):
    """SQLAlchemy 기반 Order Repository 구현체"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, order: Order) -> None:
        """주문 저장 (Late Commit - 생성 또는 업데이트)"""
        existing = self.session.query(OrderModel).filter_by(name=order.name).first()

        if existing:
            # 업데이트 (Late Commit)
            existing.date_added = order.date_added
            existing.symbol = order.symbol
            existing.trade_result_list = order.trade_result_list
            existing.order_type = order.order_type
            existing.trade_count = order.trade_count
            existing.total_count = order.total_count
            existing.remain_value = order.remain_value
            existing.total_value = order.total_value
        else:
            # 신규 삽입
            model = self._to_model(order)
            self.session.add(model)

        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def find_by_name(self, name: str) -> Optional[Order]:
        """name으로 주문 조회"""
        model = self.session.query(OrderModel).filter_by(name=name).first()
        return self._to_entity(model) if model else None

    def find_all(self) -> List[Order]:
        """전체 주문 조회 (name 오름차순)"""
        models = self.session.query(OrderModel).order_by(OrderModel.name.asc()).all()
        return [self._to_entity(model) for model in models]

    def delete_by_name(self, name: str) -> None:
        """name으로 주문 삭제"""
        try:
            orders = self.session.query(OrderModel).filter_by(name=name).all()

            if not orders:
                return

            for order in orders:
                self.session.delete(order)

            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def delete_orders(self, orders: List[Order]) -> int:
        """주문 목록 삭제 (삭제된 개수 반환)"""
        if not orders:
            return 0

        try:
            count = 0
            for order in orders:
                order_model = self.session.query(OrderModel).filter_by(name=order.name).first()
                if order_model:
                    self.session.delete(order_model)
                    count += 1

            self.session.commit()
            return count
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def find_old_orders(self, before_date: date) -> List[Order]:
        """특정 날짜 이전의 모든 주문 조회 (날짜만 비교, 시간 무시)"""
        models = self.session.query(OrderModel).filter(
            func.date(OrderModel.date_added) < before_date
        ).order_by(OrderModel.name.asc()).all()

        return [self._to_entity(model) for model in models]

    def delete_old_orders(self, before_date: date) -> int:
        """특정 날짜 이전의 모든 주문 삭제 (삭제된 개수 반환, 날짜만 비교)"""
        try:
            old_orders = self.session.query(OrderModel).filter(
                func.date(OrderModel.date_added) < before_date
            ).all()

            count = len(old_orders)

            if count == 0:
                return 0

            for order in old_orders:
                self.session.delete(order)

            self.session.commit()
            return count
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def has_sell_order_today(self, name: str) -> bool:
        """오늘 생성된 매도 주문이 있는지 확인"""
        today = date.today()
        order = self.session.query(OrderModel).filter(
            OrderModel.name == name,
            func.date(OrderModel.date_added) == today,
            OrderModel.order_type.in_([
                OrderType.SELL,
                OrderType.SELL_1_4,
                OrderType.SELL_3_4,
                OrderType.SELL_PART
            ])
        ).first()
        return order is not None

    def remove_trade_result(self, name: str, trade_result: Dict[str, Any]) -> bool:
        """특정 주문의 trade_result_list에서 거래 결과 제거 (성공 시 True)"""
        try:
            order_model = self.session.query(OrderModel).filter_by(name=name).first()

            if not order_model:
                return False

            if not order_model.trade_result_list:
                return False

            if trade_result not in order_model.trade_result_list:
                return False

            # 거래 결과 제거
            order_model.trade_result_list.remove(trade_result)
            self.session.commit()
            return True
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def find_all_by_symbol(self, symbol: str) -> List[Order]:
        """같은 symbol의 모든 Order 조회"""
        models = self.session.query(OrderModel).filter(
            OrderModel.symbol == symbol.strip().upper()
        ).order_by(OrderModel.name.asc()).all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: OrderModel) -> Order:
        """ORM Model → Entity 변환 (Mapper)"""
        return Order(
            name=model.name,
            date_added=model.date_added,
            symbol=model.symbol,
            trade_result_list=model.trade_result_list if model.trade_result_list else [],
            order_type=model.order_type,
            trade_count=model.trade_count,
            total_count=model.total_count,
            remain_value=model.remain_value,
            total_value=model.total_value
        )

    def _to_model(self, entity: Order) -> OrderModel:
        """Entity → ORM Model 변환 (Mapper)"""
        return OrderModel(
            name=entity.name,
            date_added=entity.date_added,
            symbol=entity.symbol,
            trade_result_list=entity.trade_result_list,
            order_type=entity.order_type,
            trade_count=entity.trade_count,
            total_count=entity.total_count,
            remain_value=entity.remain_value,
            total_value=entity.total_value
        )
