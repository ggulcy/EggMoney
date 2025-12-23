# -*- coding: utf-8 -*-
"""Market Data Client - yfinance를 사용한 시장 데이터 조회 (캐싱 전담)"""
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

# 프로젝트 루트 기준 데이터 디렉토리 설정
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "market_cache")
os.makedirs(DATA_DIR, exist_ok=True)


@dataclass
class CacheInfo:
    """캐시 메타데이터"""
    cached_at: str  # ISO 형식 타임스탬프
    elapsed_hours: float  # 캐시 경과 시간
    is_from_cache: bool  # 캐시에서 가져왔는지 여부


@dataclass
class TickerData:
    """티커 데이터 (캐시 정보 포함)"""
    df: pd.DataFrame
    cache_info: CacheInfo


class MarketDataClient:
    """시장 데이터 조회 클라이언트 (yfinance 사용, 캐싱 전담)"""

    def __init__(self):
        # 지연 import로 순환 참조 방지
        from config import key_store
        self._key_store = key_store

    def _get_cache_info(self, timestamp_key: str, cache_hours: int) -> Optional[CacheInfo]:
        """캐시 유효성 확인 및 CacheInfo 반환

        Args:
            timestamp_key: 타임스탬프 저장 키
            cache_hours: 캐시 유효 시간

        Returns:
            CacheInfo if 캐시 유효, None if 캐시 만료/없음
        """
        cached_timestamp = self._key_store.read(timestamp_key)
        if not cached_timestamp:
            return None

        try:
            cached_time = datetime.fromisoformat(cached_timestamp)
            elapsed_hours = (datetime.now() - cached_time).total_seconds() / 3600

            if elapsed_hours < cache_hours:
                return CacheInfo(
                    cached_at=cached_timestamp,
                    elapsed_hours=round(elapsed_hours, 2),
                    is_from_cache=True
                )
            else:
                logger.info(f"📥 캐시 만료 (경과: {elapsed_hours:.1f}시간 > {cache_hours}시간)")
                return None
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ 타임스탬프 파싱 오류: {e}")
            return None

    def _save_cache_timestamp(self, timestamp_key: str) -> str:
        """현재 시간을 캐시 타임스탬프로 저장

        Returns:
            저장된 ISO 형식 타임스탬프
        """
        now = datetime.now().isoformat()
        self._key_store.write(timestamp_key, now)
        return now

    def fetch_ticker_history(
        self,
        ticker: str,
        interval: int = 30,
        cache_hours: int = 6
    ) -> Optional[TickerData]:
        """
        특정 티커의 과거 데이터 조회 (CSV + 타임스탬프 캐싱)

        Args:
            ticker: 종목 심볼 (예: 'TQQQ', 'SOXL')
            interval: 조회 기간 (일수)
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            TickerData: DataFrame + 캐시 정보, 실패 시 None
        """
        file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
        timestamp_key = f"{ticker}_YF_DATA_TIMESTAMP"

        # 캐시 확인
        cache_info = self._get_cache_info(timestamp_key, cache_hours)
        if cache_info and os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0)
                df.index = pd.to_datetime(df.index)
                logger.info(f"📂 기존 데이터 사용 ({ticker}, 경과: {cache_info.elapsed_hours:.1f}시간)")
                return TickerData(df=df, cache_info=cache_info)
            except Exception as e:
                logger.warning(f"⚠️ 캐시 파일 읽기 실패: {e}")

        # 새로운 데이터 다운로드 (period 방식 사용)
        # interval 일수에 따라 적절한 period 선택
        if interval <= 30:
            period = "1mo"
        elif interval <= 90:
            period = "3mo"
        elif interval <= 180:
            period = "6mo"
        elif interval <= 365:
            period = "1y"
        elif interval <= 730:
            period = "2y"
        elif interval <= 1825:
            period = "5y"
        else:
            period = "max"

        try:
            df = yf.download(
                tickers=ticker,
                period=period,
                progress=False,
                group_by="ticker"
            )

            if df.empty:
                logger.error(f"❌ [{ticker}] 다운로드 실패 또는 데이터 없음")
                return None

            # 멀티 인덱스 처리
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)

            # CSV 저장 및 타임스탬프 기록
            df.to_csv(file_path)
            cached_at = self._save_cache_timestamp(timestamp_key)
            logger.info(f"✅ [{ticker}] 저장 완료: {file_path}")

            return TickerData(
                df=df,
                cache_info=CacheInfo(
                    cached_at=cached_at,
                    elapsed_hours=0.0,
                    is_from_cache=False
                )
            )

        except Exception as e:
            logger.error(f"{ticker} 조회 중 오류 발생: {e}")
            return None

    def clear_cache(self, ticker: str) -> bool:
        """
        특정 티커의 캐시(타임스탬프) 삭제

        Args:
            ticker: 캐시 삭제할 티커

        Returns:
            bool: 삭제 성공 여부
        """
        timestamp_key = f"{ticker}_YF_DATA_TIMESTAMP"
        try:
            self._key_store.delete(timestamp_key)
            logger.info(f"🗑️ [{ticker}] 캐시 타임스탬프 삭제: {timestamp_key}")
            return True
        except Exception as e:
            logger.error(f"❌ [{ticker}] 캐시 삭제 실패: {e}")
            return False
