"""Market Indicator Repository Interface - 시장 지표 저장소 인터페이스"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class MarketIndicatorRepository(ABC):
    """시장 지표 저장소 인터페이스 (추상 클래스)"""

    @abstractmethod
    def get_rsi_history(self, ticker: str, days: int = 30, period: int = 14, cache_hours: int = 6) -> Optional[List[Dict[str, Any]]]:
        """
        특정 티커의 RSI 히스토리 조회

        Args:
            ticker: 종목 심볼
            days: 조회 기간 (일수, 기본 80일)
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 56.26}, ...] 또는 None
        """
        pass

    @abstractmethod
    def get_price_history(self, ticker: str, days: int = 30, cache_hours: int = 6) -> Optional[List[Dict[str, Any]]]:
        """
        특정 티커의 가격 히스토리 조회

        Args:
            ticker: 종목 심볼
            days: 조회 기간 (일수, 기본 80일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 85.50}, ...] 또는 None
        """
        pass

    @abstractmethod
    def clear_cache(self, tickers: List[str]) -> List[str]:
        """
        특정 티커들의 캐시(타임스탬프) 삭제

        Args:
            tickers: 캐시 삭제할 티커 목록

        Returns:
            List[str]: 삭제된 캐시 키 목록
        """
        pass
