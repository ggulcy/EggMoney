# -*- coding: utf-8 -*-
"""Market Data Service - 시장 지표 계산 및 변환 로직 (캐싱은 Client에서 전담)"""
from typing import Optional
import logging
from ta.momentum import RSIIndicator as TAIndicator

from data.external.market_data.market_data_client import MarketDataClient
from domain.value_objects.market_indicator import VixIndicator, RsiIndicator

logger = logging.getLogger(__name__)


class MarketDataService:
    """시장 지표 계산 서비스 (VIX, RSI 등) - 순수 변환 로직만 담당"""

    def __init__(self, client: Optional[MarketDataClient] = None):
        self.client = client or MarketDataClient()

    def get_vix_indicator(self, cache_hours: int = 6) -> Optional[VixIndicator]:
        """
        VIX 지수 조회 및 VixIndicator 생성

        Args:
            cache_hours: 캐시 유효 시간 (Client에 전달)

        Returns:
            VixIndicator: VIX 지표 객체, 실패 시 None
        """
        vix_data = self.client.fetch_vix_data(cache_hours=cache_hours)
        if vix_data is None:
            return None

        return VixIndicator.from_value(
            vix_data.value,
            cached_at=vix_data.cache_info.cached_at,
            elapsed_hours=vix_data.cache_info.elapsed_hours
        )

    def get_rsi_indicator(
        self,
        ticker: str,
        period: int = 14,
        cache_hours: int = 6
    ) -> Optional[RsiIndicator]:
        """
        RSI 지수 계산 및 RsiIndicator 생성
        ta.momentum.RSIIndicator 사용

        Args:
            ticker: 종목 심볼
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (Client에 전달)

        Returns:
            RsiIndicator: RSI 지표 객체, 실패 시 None
        """
        ticker_data = self.client.fetch_ticker_history(
            ticker,
            interval=80,
            cache_hours=cache_hours
        )
        if ticker_data is None:
            return None

        try:
            df = ticker_data.df
            close_series = df['Close'].astype(float)

            if close_series.isnull().all():
                logger.error(f"{ticker} Close 데이터가 비어 있습니다")
                return None

            # ta 라이브러리의 RSIIndicator 사용
            rsi_series = TAIndicator(close_series, window=period).rsi()
            latest_rsi = rsi_series.dropna().iloc[-1]
            rsi_value = round(latest_rsi, 2)

            logger.info(f"✅ {ticker} RSI 계산 완료: {rsi_value}")

            return RsiIndicator.from_value(
                rsi_value,
                cached_at=ticker_data.cache_info.cached_at,
                elapsed_hours=ticker_data.cache_info.elapsed_hours
            )

        except Exception as e:
            logger.error(f"{ticker} RSI 지표 생성 중 오류: {e}")
            return None
