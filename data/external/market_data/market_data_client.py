# -*- coding: utf-8 -*-
"""Market Data Client - yfinance를 사용한 시장 데이터 조회 (캐싱 적용)"""
import os
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 프로젝트 루트 기준 데이터 디렉토리 설정
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "market_cache")
os.makedirs(DATA_DIR, exist_ok=True)


class MarketDataClient:
    """시장 데이터 조회 클라이언트 (yfinance 사용, CSV 캐싱 적용)"""

    def fetch_vix_data(self) -> Optional[pd.DataFrame]:
        """
        VIX 지수 조회 (^VIX 티커 사용)
        캐싱을 적용하여 당일 데이터가 있으면 재사용

        Returns:
            DataFrame: VIX 과거 데이터, 실패 시 None
        """
        try:
            vix_ticker = yf.Ticker("^VIX")
            hist = vix_ticker.history(period="1d")

            if hist.empty:
                logger.error("VIX 데이터를 조회할 수 없습니다")
                return None

            return hist
        except Exception as e:
            logger.error(f"VIX 조회 중 오류 발생: {e}")
            return None

    def fetch_ticker_history(
        self,
        ticker: str,
        interval: int = 80,
        use_cache: bool = True,
        cache_hours: int = 6
    ) -> Optional[pd.DataFrame]:
        """
        특정 티커의 과거 데이터 조회 (시간 단위 캐싱)

        Args:
            ticker: 종목 심볼 (예: 'TQQQ', 'SOXL')
            interval: 조회 기간 (일수)
            use_cache: 캐시 사용 여부
            cache_hours: 캐시 유효 시간 (시간 단위, 기본 6시간)

        Returns:
            DataFrame: 티커 과거 데이터, 실패 시 None
        """
        from config import key_store

        file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
        timestamp_key = f"{ticker}_YF_DATA_TIMESTAMP"

        # 캐시 확인
        if use_cache and os.path.exists(file_path):
            cached_timestamp = key_store.read(timestamp_key)

            if cached_timestamp:
                try:
                    cached_time = datetime.fromisoformat(cached_timestamp)
                    now = datetime.now()
                    time_diff = (now - cached_time).total_seconds() / 3600  # 시간 단위

                    if time_diff < cache_hours:
                        df = pd.read_csv(file_path, index_col=0)
                        df.index = pd.to_datetime(df.index)
                        logger.info(f"📂 기존 데이터 사용 ({ticker}, 경과: {time_diff:.1f}시간)")
                        return df
                    else:
                        logger.info(f"📥 [{ticker}] 캐시 만료 (경과: {time_diff:.1f}시간 > {cache_hours}시간)")
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ 타임스탬프 파싱 오류: {e} → 재다운로드 진행")

        # 새로운 데이터 다운로드
        today = datetime.today().date()
        start_date = today - timedelta(days=interval)
        end_date = today

        try:
            df = yf.download(
                tickers=ticker,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
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
            now = datetime.now().isoformat()
            key_store.write(timestamp_key, now)
            logger.info(f"✅ [{ticker}] 저장 완료: {file_path}")

            return df

        except Exception as e:
            logger.error(f"{ticker} 조회 중 오류 발생: {e}")
            return None

