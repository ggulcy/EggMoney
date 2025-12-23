# -*- coding: utf-8 -*-
"""Message Repository Interface - 메시지 발송 추상화"""
from abc import ABC, abstractmethod
from typing import Optional


class MessageRepository(ABC):
    """
    메시지 발송 인터페이스

    메시지 발송 서비스(텔레그램, 슬랙 등)를 추상화하여
    비즈니스 로직에서 구현체에 의존하지 않도록 함
    """

    @abstractmethod
    def send_message(self, message: str, photo_path: Optional[str] = None) -> None:
        """
        메시지 발송

        Args:
            message: 전송할 메시지
            photo_path: 전송할 사진 경로 (선택적)
                - None: 텍스트 메시지만 전송
                - 경로 지정: 사진과 함께 전송
        """
        ...
