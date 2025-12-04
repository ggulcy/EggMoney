# -*- coding: utf-8 -*-
"""Market Indicator Repository Implementation - MarketIndicatorRepository 구현체"""
from typing import Optional
import logging

from domain.repositories.market_indicator_repository import MarketIndicatorRepository
from domain.value_objects.market_indicator import VixIndicator, RsiIndicator
from data.external.market_data.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class MarketIndicatorRepositoryImpl(MarketIndicatorRepository):
    """MarketIndicatorRepository 구현체 (yfinance 기반)"""

    def __init__(self):
        self.service = MarketDataService()

    def get_vix(self, cache_hours: int = 6) -> Optional[VixIndicator]:
        """
        VIX 공포 지수 조회 (시간 단위 캐싱)

        Args:
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            VixIndicator 또는 None (조회 실패 시)
        """
        try:
            return self.service.get_vix_indicator(cache_hours=cache_hours)
        except Exception as e:
            logger.error(f"VIX 조회 실패: {e}")
            return None

    def get_rsi(self, ticker: str, period: int = 14, cache_hours: int = 6) -> Optional[RsiIndicator]:
        """
        특정 티커의 RSI 지수 조회 (시간 단위 캐싱)

        Args:
            ticker: 종목 심볼 (예: 'TQQQ', 'SOXL')
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            RsiIndicator 또는 None (조회 실패 시)
        """
        try:
            return self.service.get_rsi_indicator(ticker, period, cache_hours=cache_hours)
        except Exception as e:
            logger.error(f"{ticker} RSI 조회 실패: {e}")
            return None
