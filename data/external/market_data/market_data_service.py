# -*- coding: utf-8 -*-
"""Market Data Service - 시장 지표 계산 및 변환 로직 (캐싱 적용)"""
from datetime import datetime
import pandas as pd
from typing import Optional
import logging
from ta.momentum import RSIIndicator as TAIndicator

from data.external.market_data.market_data_client import MarketDataClient
from domain.value_objects.market_indicator import VixIndicator, RsiIndicator

logger = logging.getLogger(__name__)


class MarketDataService:
    """시장 지표 계산 서비스 (VIX, RSI 등) - 캐싱 적용"""

    def __init__(self):
        self.client = MarketDataClient()

    def get_vix_indicator(self, cache_hours: int = 6) -> Optional[VixIndicator]:
        """
        VIX 지수 조회 및 VixIndicator 생성 (시간 단위 캐싱)

        Args:
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            VixIndicator: VIX 지표 객체, 실패 시 None
        """
        from config import key_store

        VIX_DATA_TIMESTAMP = "VIX_DATA_TIMESTAMP"
        VIX_DATA = "VIX_DATA"

        # 캐시 확인
        cached_timestamp = key_store.read(VIX_DATA_TIMESTAMP)
        cached_data = key_store.read(VIX_DATA)

        # 캐시 유효성 검사
        if cached_timestamp and cached_data:
            try:
                cached_time = datetime.fromisoformat(cached_timestamp)
                now = datetime.now()
                time_diff = (now - cached_time).total_seconds() / 3600  # 시간 단위

                if time_diff < cache_hours:
                    logger.info(f"📂 VIX 캐시 데이터 사용 (경과: {time_diff:.1f}시간)")
                    # cached_data는 (value, level) 형태 (JSON에서 list로 변환될 수 있음)
                    if (isinstance(cached_data, (tuple, list)) and len(cached_data) == 2):
                        return VixIndicator(
                            value=cached_data[0],
                            level=cached_data[1],
                            cached_at=cached_timestamp,
                            elapsed_hours=round(time_diff, 2)
                        )
            except (ValueError, TypeError) as e:
                logger.warning(f"캐시 타임스탬프 파싱 실패: {e}")

        # 새로운 데이터 조회
        try:
            df = self.client.fetch_vix_data()
            if df is None or df.empty:
                logger.error("VIX 데이터 조회 실패")
                return None

            # 최신 종가 가져오기
            vix_value = round(df['Close'].iloc[-1], 2)
            logger.info(f"✅ VIX 조회 성공: {vix_value}")

            # 캐시에 저장 (현재 시간을 ISO 형식으로 저장)
            now = datetime.now().isoformat()
            key_store.write(VIX_DATA_TIMESTAMP, now)

            vix_indicator = VixIndicator.from_value(
                vix_value,
                cached_at=now,
                elapsed_hours=0.0
            )

            key_store.write(VIX_DATA, (vix_indicator.value, vix_indicator.level))

            return vix_indicator

        except Exception as e:
            logger.error(f"VIX 지표 생성 중 오류: {e}")
            return None

    def get_rsi_indicator(self, ticker: str, period: int = 14, cache_hours: int = 6) -> Optional[RsiIndicator]:
        """
        RSI 지수 계산 및 RsiIndicator 생성 (시간 단위 캐싱)
        ta.momentum.RSIIndicator 사용

        Args:
            ticker: 종목 심볼
            period: RSI 계산 기간 (기본 14일)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            RsiIndicator: RSI 지표 객체, 실패 시 None
        """
        from config import key_store

        timestamp_key = f"{ticker}_YF_DATA_TIMESTAMP"

        try:
            # 충분한 기간의 데이터 조회 (시간 단위 캐싱 적용)
            df = self.client.fetch_ticker_history(ticker, interval=80, cache_hours=cache_hours)
            if df is None or df.empty:
                logger.error(f"{ticker} 데이터 조회 실패")
                return None

            # Close 데이터 추출
            close_series = df['Close'].astype(float)

            if close_series.isnull().all():
                logger.error(f"{ticker} Close 데이터가 비어 있습니다")
                return None

            # ta 라이브러리의 RSIIndicator 사용
            rsi_series = TAIndicator(close_series, window=period).rsi()
            latest_rsi = rsi_series.dropna().iloc[-1]
            rsi_value = round(latest_rsi, 2)

            logger.info(f"✅ {ticker} RSI 조회 성공: {rsi_value}")

            # 캐시 메타데이터 계산
            cached_timestamp = key_store.read(timestamp_key)
            if cached_timestamp:
                try:
                    cached_time = datetime.fromisoformat(cached_timestamp)
                    elapsed_hours = (datetime.now() - cached_time).total_seconds() / 3600
                    return RsiIndicator.from_value(
                        rsi_value,
                        cached_at=cached_timestamp,
                        elapsed_hours=round(elapsed_hours, 2)
                    )
                except (ValueError, TypeError):
                    pass

            # 새로 생성된 데이터 (elapsed_hours=0)
            now = datetime.now().isoformat()
            return RsiIndicator.from_value(
                rsi_value,
                cached_at=now,
                elapsed_hours=0.0
            )

        except Exception as e:
            logger.error(f"{ticker} RSI 지표 생성 중 오류: {e}")
            return None
