"""Domain Repository Interfaces"""
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository

__all__ = ['BotInfoRepository', 'TradeRepository']
from domain.repositories.history_repository import HistoryRepository

__all__.append('HistoryRepository')
from domain.repositories.order_repository import OrderRepository

__all__.append('OrderRepository')
from domain.repositories.status_repository import StatusRepository

__all__.append('StatusRepository')
