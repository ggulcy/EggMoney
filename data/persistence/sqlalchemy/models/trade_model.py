"""Trade ORM Model - 거래 정보 SQLAlchemy 모델"""
from sqlalchemy import Column, String, Float, Enum, DateTime
from data.persistence.sqlalchemy.core.base import Base
from domain.value_objects.trade_type import TradeType


class TradeModel(Base):
    """Trade 테이블 ORM 모델"""

    __tablename__ = 'trade'

    # Composite Primary Key
    date_added = Column(DateTime, primary_key=True, nullable=False)
    name = Column(String, primary_key=True, nullable=False, index=True)
    symbol = Column(String, primary_key=True, nullable=False, index=True)

    # Trade 정보
    latest_date_trade = Column(DateTime, nullable=False)
    purchase_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False, index=True)
    trade_type = Column(Enum(TradeType), nullable=False)
    total_price = Column(Float, nullable=False)

    def __repr__(self):
        return (
            f"<TradeModel(date_added={self.date_added}, name={self.name}, "
            f"symbol={self.symbol}, purchase_price={self.purchase_price}, "
            f"amount={self.amount}, trade_type={self.trade_type.value})>"
        )
