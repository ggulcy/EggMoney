# -*- coding: utf-8 -*-
"""Market Data Service - 시장 지표 계산 및 변환 로직 (캐싱은 Client에서 전담)"""
from typing import Optional, List, Dict, Any
import logging
from ta.momentum import RSIIndicator as TAIndicator

from data.external.market_data.market_data_client import MarketDataClient

logger = logging.getLogger(__name__)


class MarketDataService:
    """시장 지표 계산 서비스 (VIX, RSI 등) - 순수 변환 로직만 담당"""

    def __init__(self, client: Optional[MarketDataClient] = None):
        self.client = client or MarketDataClient()

    # 캐시 통일을 위한 고정 interval (3개월치 데이터)
    CACHE_INTERVAL = 90

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
            days: 반환할 데이터 개수 (일수, 기본 30일, 최대 66일)
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 56.26}, ...] 또는 None
        """
        # RSI 계산에 period일 필요하므로 최대 유효 days = CACHE_INTERVAL - period
        max_days = self.CACHE_INTERVAL - period
        if days > max_days:
            logger.warning(f"days({days})가 최대값({max_days})을 초과하여 {max_days}로 조정")
            days = max_days

        try:
            # 항상 80일치 데이터 캐시 사용
            ticker_data = self.client.fetch_ticker_history(
                ticker,
                interval=self.CACHE_INTERVAL,
                cache_hours=cache_hours
            )
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
        days: int,
        cache_hours: int = 6
    ) -> Optional[List[Dict[str, Any]]]:
        """
        특정 티커의 가격 히스토리 조회

        Args:
            ticker: 종목 심볼
            days: 반환할 데이터 개수 (일수, 기본 30일, 최대 80일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            List[Dict]: [{"date": "2025-12-01", "value": 85.50}, ...] 또는 None
        """
        # 최대 유효 days = CACHE_INTERVAL
        if days > self.CACHE_INTERVAL:
            logger.warning(f"days({days})가 최대값({self.CACHE_INTERVAL})을 초과하여 {self.CACHE_INTERVAL}로 조정")
            days = self.CACHE_INTERVAL

        try:
            # 항상 80일치 데이터 캐시 사용
            ticker_data = self.client.fetch_ticker_history(
                ticker,
                interval=self.CACHE_INTERVAL,
                cache_hours=cache_hours
            )
            if ticker_data is None:
                return None

            # 최근 days일만 추출
            df = ticker_data.df.tail(days)
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

    def clear_cache(self, ticker: str) -> bool:
        """
        특정 티커의 캐시(타임스탬프) 삭제

        Args:
            ticker: 캐시 삭제할 티커

        Returns:
            bool: 삭제 성공 여부
        """
        return self.client.clear_cache(ticker)

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
            # 60일 이평선 계산을 위해 최소 60일치 데이터 필요
            ticker_data = self.client.fetch_ticker_history(
                ticker,
                interval=self.CACHE_INTERVAL,
                cache_hours=cache_hours
            )
            if ticker_data is None:
                return None

            df = ticker_data.df
            close_series = df['Close'].astype(float)

            if close_series.isnull().all():
                logger.error(f"{ticker} Close 데이터가 비어 있습니다")
                return None

            # 이동평균 계산
            ma20 = close_series.rolling(window=20).mean()
            ma60 = close_series.rolling(window=60).mean()

            # 최신 값 추출
            current_price = round(float(close_series.iloc[-1]), 2)
            ma20_value = round(float(ma20.iloc[-1]), 2)
            ma60_value = round(float(ma60.iloc[-1]), 2)

            return {
                "current_price": current_price,
                "ma20": ma20_value,
                "ma60": ma60_value,
                "values": [current_price, ma20_value, ma60_value]
            }
        except Exception as e:
            logger.error(f"{ticker} 이평선 상태 조회 실패: {e}")
            return None
