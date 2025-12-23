"""External Telegram API Integration"""
from data.external.telegram.telegram_data_source import send_message_sync
from data.external.telegram.telegram_message_repository_impl import TelegramMessageRepositoryImpl

__all__ = [
    'send_message_sync',
    'TelegramMessageRepositoryImpl',
]
