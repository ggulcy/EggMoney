"""Domain Repository Interfaces"""
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository
from domain.repositories.history_repository import HistoryRepository
from domain.repositories.order_repository import OrderRepository
from domain.repositories.exchange_repository import ExchangeRepository
from domain.repositories.message_repository import MessageRepository

__all__ = [
    'BotInfoRepository',
    'TradeRepository',
    'HistoryRepository',
    'OrderRepository',
    'ExchangeRepository',
    'MessageRepository',
]
