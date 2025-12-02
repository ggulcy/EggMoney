"""Status ORM Model"""
from sqlalchemy import Column, Integer, Float
from data.persistence.sqlalchemy.core.base import Base


class StatusModel(Base):
    """입출금 상태 ORM 모델"""
    __tablename__ = 'status'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 입출금 정보
    deposit_won = Column(Float, nullable=False, default=0)
    deposit_dollar = Column(Float, nullable=False, default=0)
    withdraw_won = Column(Float, nullable=False, default=0)
    withdraw_dollar = Column(Float, nullable=False, default=0)

    def __repr__(self):
        return (f"<StatusModel(id={self.id}, "
                f"deposit_won={self.deposit_won}, deposit_dollar={self.deposit_dollar}, "
                f"withdraw_won={self.withdraw_won}, withdraw_dollar={self.withdraw_dollar})>")
