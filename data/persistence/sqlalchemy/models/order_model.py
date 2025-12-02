"""Order ORM Model"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.ext.mutable import MutableList
from data.persistence.sqlalchemy.core.base import Base
from domain.value_objects.order_type import OrderType


class OrderModel(Base):
    """TWAP 주문 ORM 모델"""
    __tablename__ = 'order'

    # Primary Key
    name = Column(String, primary_key=True, nullable=False)

    # 주문 정보
    date_added = Column(DateTime, nullable=False)
    symbol = Column(String, nullable=False)
    trade_result_list = Column(MutableList.as_mutable(JSON), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False)

    # 진행 상황
    trade_count = Column(Integer, nullable=False)
    total_count = Column(Integer, nullable=False)

    # 금액 정보
    remain_value = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)

    def __repr__(self):
        trade_results_str = ""
        if self.trade_result_list:
            trade_results_str = "\n    ".join([str(tr) for tr in self.trade_result_list])
            trade_results_str = f"\n    {trade_results_str}"
        else:
            trade_results_str = "[]"

        return (
            f"<OrderModel(\n"
            f"  date_added={self.date_added},\n"
            f"  name={self.name},\n"
            f"  symbol={self.symbol},\n"
            f"  order_type={self.order_type},\n"
            f"  trade_count={self.trade_count}/{self.total_count},\n"
            f"  remain_value={self.remain_value},\n"
            f"  total_value={self.total_value},\n"
            f"  trade_result_list={trade_results_str}\n"
            f")>"
        )
