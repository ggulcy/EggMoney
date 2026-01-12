# -*- coding: utf-8 -*-
"""Market Indicator Repository Implementation - MarketIndicatorRepository 구현체"""
from typing import Optional, List, Dict, Any
import logging

from domain.repositories.market_indicator_repository import MarketIndicatorRepository
from data.external.market_data.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class MarketIndicatorRepositoryImpl(MarketIndicatorRepository):
    """MarketIndicatorRepository 구현체 (yfinance 기반)"""

    def __init__(self):
        self.service = MarketDataService()

    def get_rsi_history(
        self,
        ticker: str,
        days: int = 30,
        period: int = 14,
        cache_hours: int = 6
    ) -> Optional[List[Dict[str, Any]]]:
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
        try:
            return self.service.get_rsi_history(
                ticker=ticker,
                days=days,
                period=period,
                cache_hours=cache_hours
            )
        except Exception as e:
            logger.error(f"{ticker} RSI 히스토리 조회 실패: {e}")
            return None

    def get_price_history(
        self,
        ticker: str,
        days: int = 90,
        cache_hours: int = 6
    ) -> Optional[List[Dict[str, Any]]]:
        """
        특정 티커의 가격 히스토리 조회

        Args:
            ticker: 종목 심볼
            days: 조회 기간 (일수, 기본 80일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 85.50}, ...] 또는 None
        """
        try:
            return self.service.get_price_history(
                ticker=ticker,
                days=days,
                cache_hours=cache_hours
            )
        except Exception as e:
            logger.error(f"{ticker} 가격 히스토리 조회 실패: {e}")
            return None

    def clear_cache(self, tickers: list) -> list:
        """
        특정 티커들의 캐시(타임스탬프) 삭제

        Args:
            tickers: 캐시 삭제할 티커 목록

        Returns:
            List[str]: 삭제된 티커 목록
        """
        cleared = []
        for ticker in tickers:
            if self.service.clear_cache(ticker):
                cleared.append(ticker)
        return cleared

    def get_moving_average_status(
        self,
        ticker: str,
        cache_hours: int = 6
    ) -> Optional[Dict[str, Any]]:
        """
        특정 티커의 이평선 상태 조회 (현재가, 20일선, 60일선)

        Args:
            ticker: 종목 심볼
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            Dict: {
                "current_price": 현재가,
                "ma20": 20일 이동평균,
                "ma60": 60일 이동평균,
                "values": [현재가, 20일선, 60일선]
            } 또는 None
        """
        try:
            return self.service.get_moving_average_status(
                ticker=ticker,
                cache_hours=cache_hours
            )
        except Exception as e:
            logger.error(f"{ticker} 이평선 상태 조회 실패: {e}")
            return None
