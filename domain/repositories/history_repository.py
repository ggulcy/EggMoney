"""History Repository Interface"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from domain.entities.history import History


class HistoryRepository(ABC):
    """거래 이력 저장소 인터페이스"""

    @abstractmethod
    def save(self, history: History) -> None:
        """히스토리 저장"""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[History]:
        """name으로 첫 번째 히스토리 조회"""
        pass

    @abstractmethod
    def find_all(self) -> List[History]:
        """전체 히스토리 조회 (sell_date 역순)"""
        pass

    @abstractmethod
    def find_by_name_all(self, name: str) -> List[History]:
        """name으로 모든 히스토리 조회"""
        pass

    @abstractmethod
    def find_by_name_and_date(self, name: str, date: datetime) -> List[History]:
        """name과 date_added로 히스토리 조회"""
        pass

    @abstractmethod
    def find_today_sell_by_name(self, name: str) -> Optional[History]:
        """오늘의 첫 번째 매도 히스토리 조회 (매도 거래만)"""
        pass

    @abstractmethod
    def find_by_year_month(self, year: int, month: int, symbol: Optional[str] = None) -> List[History]:
        """연월별 히스토리 조회 (선택적 symbol 필터)"""
        pass

    @abstractmethod
    def get_total_sell_profit(self) -> float:
        """전체 매도 총 수익 (매도 거래만)"""
        pass

    @abstractmethod
    def get_total_sell_profit_by_name(self, name: str) -> float:
        """name별 매도 총 수익 (매도 거래만)"""
        pass

    @abstractmethod
    def get_total_sell_profit_by_symbol(self, symbol: str) -> float:
        """symbol별 매도 총 수익 (매도 거래만)"""
        pass

    @abstractmethod
    def get_total_sell_profit_by_name_and_date(self, name: str, date: datetime) -> float:
        """name과 date_added별 매도 총 수익 (매도 거래만)"""
        pass

    @abstractmethod
    def get_total_sell_profit_by_year(self, year: int) -> float:
        """연도별 매도 총 수익 (매도 거래만)"""
        pass

    @abstractmethod
    def get_monthly_sell_profit_by_year(self, year: int) -> List[tuple]:
        """연도별 월별 매도 수익 [(month, total_profit), ...] (매도 거래만)"""
        pass

    @abstractmethod
    def get_years_from_sell_date(self) -> List[int]:
        """sell_date에서 연도 목록 추출 (중복 제거, 정렬)"""
        pass

    @abstractmethod
    def delete_by_name(self, name: str) -> None:
        """name으로 모든 히스토리 삭제"""
        pass

    @abstractmethod
    def delete(self, name: str, date_added: datetime) -> None:
        """특정 히스토리 삭제 (PK 기반)"""
        pass

    @abstractmethod
    def sync_all(self, history_list: List[History]) -> None:
        """전체 동기화 (기존 데이터 삭제 후 재삽입)"""
        pass

    @abstractmethod
    def find_today_sells(self) -> List[History]:
        """
        오늘 매도한 History 리스트 조회

        sell_date가 오늘 날짜인 History들을 반환
        매도 거래는 Trade를 삭제하고 History에 기록되므로
        History의 sell_date로 판단

        Returns:
            List[History]: 오늘 매도한 History 리스트 (최신순)
        """
        pass
