"""Market Indicator Repository Interface - 시장 지표 저장소 인터페이스"""
from abc import ABC, abstractmethod
from typing import Optional
from domain.value_objects.market_indicator import VixIndicator, RsiIndicator


class MarketIndicatorRepository(ABC):
    """시장 지표 저장소 인터페이스 (추상 클래스)"""

    @abstractmethod
    def get_vix(self) -> Optional[VixIndicator]:
        """
        VIX 공포 지수 조회

        Returns:
            VixIndicator 또는 None (조회 실패 시)
        """
        pass

    @abstractmethod
    def get_rsi(self, ticker: str, period: int = 14) -> Optional[RsiIndicator]:
        """
        특정 티커의 RSI 지수 조회

        Args:
            ticker: 종목 심볼 (예: 'TQQQ', 'SOXL')
            period: RSI 계산 기간 (기본 14일)

        Returns:
            RsiIndicator 또는 None (조회 실패 시)
        """
        pass
