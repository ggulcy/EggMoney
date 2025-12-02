"""Status Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.status import Status


class StatusRepository(ABC):
    """입출금 상태 저장소 인터페이스"""

    @abstractmethod
    def get_status(self) -> Optional[Status]:
        """상태 조회 (단일 레코드)"""
        pass

    @abstractmethod
    def sync_status(self, status: Status) -> None:
        """상태 동기화 (기존 데이터 삭제 후 새로 저장)"""
        pass
