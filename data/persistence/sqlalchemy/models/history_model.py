"""History ORM Model"""
from sqlalchemy import Column, String, Float, DateTime, Enum as SQLEnum
from data.persistence.sqlalchemy.core.base import Base
from domain.value_objects.trade_type import TradeType


class HistoryModel(Base):
    """거래 이력 ORM 모델"""
    __tablename__ = 'history'

    # 복합 Primary Key: (date_added, sell_date, trade_type, name)
    date_added = Column(DateTime, primary_key=True, nullable=False)
    sell_date = Column(DateTime, primary_key=True, nullable=False)
    trade_type = Column(SQLEnum(TradeType), primary_key=True, nullable=False)
    name = Column(String, primary_key=True, nullable=False)

    # 일반 필드
    symbol = Column(String, nullable=False)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    profit_rate = Column(Float, nullable=False)

    def __repr__(self):
        return (f"<HistoryModel(date_added={self.date_added}, sell_date={self.sell_date}, "
                f"trade_type={self.trade_type}, name={self.name}, symbol={self.symbol}, "
                f"buy_price={self.buy_price}, sell_price={self.sell_price}, "
                f"profit={self.profit}, profit_rate={self.profit_rate})>")
