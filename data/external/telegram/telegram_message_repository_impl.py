# -*- coding: utf-8 -*-
"""Telegram MessageRepository 구현체"""
from typing import Optional

from domain.repositories import MessageRepository
from data.external.telegram.telegram_data_source import send_message_sync

# 텔레그램 메시지 최대 길이 (4096자 제한, 안전하게 3000자로 설정)
MAX_TELEGRAM_MESSAGE_LENGTH = 3000


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
        # 메시지 길이 제한 (텔레그램 4096자 제한)
        if len(message) > MAX_TELEGRAM_MESSAGE_LENGTH:
            truncated_message = message[:MAX_TELEGRAM_MESSAGE_LENGTH - 100]
            truncated_message += f"\n\n... (메시지가 너무 길어 {len(message) - MAX_TELEGRAM_MESSAGE_LENGTH + 100}자 생략됨)"
            send_message_sync(truncated_message, photo_path)
        else:
            send_message_sync(message, photo_path)
