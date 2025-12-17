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
        days: int = 30,
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


