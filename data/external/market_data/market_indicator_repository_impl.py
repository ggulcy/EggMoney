# -*- coding: utf-8 -*-
"""Market Indicator Repository Implementation - MarketIndicatorRepository 구현체"""
from typing import Optional, List, Dict, Any
import logging
from ta.momentum import RSIIndicator as TAIndicator

from domain.repositories.market_indicator_repository import MarketIndicatorRepository
from domain.value_objects.market_indicator import VixIndicator, RsiIndicator
from data.external.market_data.market_data_service import MarketDataService
from data.external.market_data.market_data_client import MarketDataClient

logger = logging.getLogger(__name__)


class MarketIndicatorRepositoryImpl(MarketIndicatorRepository):
    """MarketIndicatorRepository 구현체 (yfinance 기반)"""

    def __init__(self):
        self.service = MarketDataService()
        self.client = MarketDataClient()

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

    def get_vix_history(self, days: int = 30, cache_hours: int = 6) -> Optional[List[Dict[str, Any]]]:
        """
        VIX 히스토리 조회

        Args:
            days: 조회 기간 (일수, 기본 30일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 15.78}, ...] 또는 None
        """
        try:
            ticker_data = self.client.fetch_vix_history(cache_hours=cache_hours)
            if ticker_data is None:
                return None

            df = ticker_data.df.tail(days)
            result = []
            for idx, row in df.iterrows():
                result.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "value": round(float(row['Close']), 2)
                })

            return result
        except Exception as e:
            logger.error(f"VIX 히스토리 조회 실패: {e}")
            return None

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
            days: 조회 기간 (일수, 기본 30일)
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 56.26}, ...] 또는 None
        """
        try:
            # RSI 계산에 period일이 추가로 필요하므로 days + period 만큼 조회
            ticker_data = self.client.fetch_ticker_history(ticker, interval=days + period, cache_hours=cache_hours)
            if ticker_data is None:
                return None

            df = ticker_data.df
            close_series = df['Close'].astype(float)

            if close_series.isnull().all():
                logger.error(f"{ticker} Close 데이터가 비어 있습니다")
                return None

            # RSI 계산
            rsi_series = TAIndicator(close_series, window=period).rsi()

            # 최근 days일만 추출
            rsi_df = rsi_series.dropna().tail(days)

            result = []
            for idx, value in rsi_df.items():
                result.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "value": round(float(value), 2)
                })

            return result
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
            days: 조회 기간 (일수, 기본 30일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 85.50}, ...] 또는 None
        """
        try:
            ticker_data = self.client.fetch_ticker_history(ticker, interval=days, cache_hours=cache_hours)
            if ticker_data is None:
                return None

            df = ticker_data.df
            result = []
            for idx, row in df.iterrows():
                result.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "value": round(float(row['Close']), 2)
                })

            return result
        except Exception as e:
            logger.error(f"{ticker} 가격 히스토리 조회 실패: {e}")
            return None


