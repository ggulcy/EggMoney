"""SQLAlchemy Repository Implementations"""
from data.persistence.sqlalchemy.repositories.bot_info_repository_impl import SQLAlchemyBotInfoRepositoryImpl
from data.persistence.sqlalchemy.repositories.trade_repository_impl import SQLAlchemyTradeRepositoryImpl
from data.persistence.sqlalchemy.repositories.history_repository_impl import SQLAlchemyHistoryRepositoryImpl
from data.persistence.sqlalchemy.repositories.order_repository_impl import SQLAlchemyOrderRepositoryImpl

# 하위 호환성을 위한 별칭 (deprecated, 추후 제거 예정)
SQLAlchemyBotInfoRepository = SQLAlchemyBotInfoRepositoryImpl
SQLAlchemyTradeRepository = SQLAlchemyTradeRepositoryImpl
SQLAlchemyHistoryRepository = SQLAlchemyHistoryRepositoryImpl
SQLAlchemyOrderRepository = SQLAlchemyOrderRepositoryImpl

__all__ = [
    # New names with Impl suffix
    'SQLAlchemyBotInfoRepositoryImpl',
    'SQLAlchemyTradeRepositoryImpl',
    'SQLAlchemyHistoryRepositoryImpl',
    'SQLAlchemyOrderRepositoryImpl',
    # Deprecated aliases
    'SQLAlchemyBotInfoRepository',
    'SQLAlchemyTradeRepository',
    'SQLAlchemyHistoryRepository',
    'SQLAlchemyOrderRepository',
]
