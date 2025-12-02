"""BotInfo Repository Interface - 봇 정보 저장소 인터페이스"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.bot_info import BotInfo


class BotInfoRepository(ABC):
    """BotInfo 저장소 인터페이스 (추상 클래스)"""

    @abstractmethod
    def save(self, bot_info: BotInfo) -> None:
        """
        BotInfo 저장 (신규 또는 업데이트)

        Args:
            bot_info: 저장할 BotInfo 엔티티
        """
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[BotInfo]:
        """
        이름으로 BotInfo 조회

        Args:
            name: 봇 이름

        Returns:
            BotInfo 또는 None
        """
        pass

    @abstractmethod
    def find_all(self) -> List[BotInfo]:
        """
        모든 BotInfo 조회

        Returns:
            BotInfo 리스트
        """
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: str) -> List[BotInfo]:
        """
        심볼로 BotInfo 리스트 조회 (동일 종목의 여러 봇)

        Args:
            symbol: 종목 심볼 (예: 'SOXL')

        Returns:
            BotInfo 리스트
        """
        pass

    @abstractmethod
    def find_active_bots(self) -> List[BotInfo]:
        """
        활성화된 BotInfo 리스트 조회

        Returns:
            active=True인 BotInfo 리스트
        """
        pass

    @abstractmethod
    def delete(self, name: str) -> None:
        """
        BotInfo 삭제

        Args:
            name: 삭제할 봇 이름
        """
        pass
