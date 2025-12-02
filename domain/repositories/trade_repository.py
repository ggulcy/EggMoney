"""Trade Repository Interface - 거래 정보 저장소 인터페이스"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.trade import Trade


class TradeRepository(ABC):
    """Trade 저장소 인터페이스 (추상 클래스)"""

    @abstractmethod
    def save(self, trade: Trade) -> None:
        """
        Trade 저장 (신규 또는 업데이트)

        Args:
            trade: 저장할 Trade 엔티티
        """
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Trade]:
        """
        이름으로 Trade 조회 (purchase_price 오름차순 기준 첫 번째)

        Args:
            name: 봇 이름

        Returns:
            Trade 또는 None
        """
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: str) -> Optional[Trade]:
        """
        심볼로 Trade 조회 (purchase_price 오름차순 기준 첫 번째)

        Args:
            symbol: 종목 심볼

        Returns:
            Trade 또는 None
        """
        pass

    @abstractmethod
    def find_all_by_symbol(self, symbol: str) -> List[Trade]:
        """
        심볼로 모든 Trade 조회 (purchase_price 오름차순)

        Args:
            symbol: 종목 심볼

        Returns:
            Trade 리스트
        """
        pass

    @abstractmethod
    def find_latest_by_symbol(self, symbol: str) -> Optional[Trade]:
        """
        심볼로 최신 Trade 조회 (date_added 내림차순 기준 첫 번째)

        Args:
            symbol: 종목 심볼

        Returns:
            Trade 또는 None
        """
        pass

    @abstractmethod
    def find_highest_price_by_symbol(self, symbol: str) -> Optional[Trade]:
        """
        심볼로 최고가 Trade 조회 (purchase_price 내림차순 기준 첫 번째)

        Args:
            symbol: 종목 심볼

        Returns:
            Trade 또는 None
        """
        pass

    @abstractmethod
    def find_all(self) -> List[Trade]:
        """
        모든 Trade 조회 (name, date_added 오름차순)

        Returns:
            Trade 리스트
        """
        pass

    @abstractmethod
    def find_active_trades(self) -> List[Trade]:
        """
        활성 Trade 조회 (amount > 0, name != "RP")

        Returns:
            Trade 리스트
        """
        pass

    @abstractmethod
    def get_active_trade_count(self) -> int:
        """
        활성 Trade 개수 조회

        Returns:
            int: 활성 거래 개수
        """
        pass

    @abstractmethod
    def get_total_investment(self, name: str) -> float:
        """
        총 투자금 조회 (amount * purchase_price의 합계)

        Args:
            name: 봇 이름

        Returns:
            float: 총 투자금
        """
        pass

    @abstractmethod
    def get_average_purchase_price(self, name: str) -> Optional[float]:
        """
        평균 매수 단가 조회

        Args:
            name: 봇 이름

        Returns:
            float: 평균 매수 단가 또는 None
        """
        pass

    @abstractmethod
    def get_total_amount(self, name: str) -> float:
        """
        총 보유 수량 조회

        Args:
            name: 봇 이름

        Returns:
            float: 총 보유 수량
        """
        pass

    @abstractmethod
    def delete_by_name(self, name: str) -> None:
        """
        이름으로 Trade 삭제 (단일 레코드)

        Args:
            name: 봇 이름
        """
        pass

    @abstractmethod
    def delete_all_by_name(self, name: str) -> None:
        """
        이름으로 모든 Trade 삭제

        Args:
            name: 봇 이름
        """
        pass

    @abstractmethod
    def rebalance_trade(
        self,
        name: str,
        symbol: str,
        prev_trade: Optional[Trade],
        trade_result: 'TradeResult'
    ) -> Trade:
        """
        Trade 리밸런싱 (매수/매도 후 평단가 재계산)

        Args:
            name: 봇 이름
            symbol: 종목 심볼
            prev_trade: 이전 거래 정보 (없으면 None)
            trade_result: 거래 결과

        Returns:
            Trade: 리밸런싱된 Trade

        egg/repository/trade_repository.py의 re_balancing_trade() 참고
        """
        pass

    @abstractmethod
    def get_all_tickers(self) -> List[str]:
        """
        모든 고유 티커(심볼) 조회

        Returns:
            List[str]: 티커 리스트
        """
        pass

    @abstractmethod
    def sync_all(self, trades: List[Trade]) -> None:
        """
        전체 Trade 동기화 (기존 데이터 삭제 후 새 데이터 삽입)

        Args:
            trades: Trade 리스트
        """
        pass
