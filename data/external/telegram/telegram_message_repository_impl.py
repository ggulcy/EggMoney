# -*- coding: utf-8 -*-
"""Telegram MessageRepository 구현체"""
from typing import Optional

from domain.repositories import MessageRepository
from data.external.telegram.telegram_data_source import send_message_sync


class TelegramMessageRepositoryImpl(MessageRepository):
    """
    텔레그램 MessageRepository 구현체

    텔레그램 봇을 통해 메시지를 발송하는 구현체
    """

    def send_message(self, message: str, photo_path: Optional[str] = None) -> None:
        """
        텔레그램으로 메시지 발송

        Args:
            message: 전송할 메시지
            photo_path: 전송할 사진 경로 (선택적)
        """
        send_message_sync(message, photo_path)
