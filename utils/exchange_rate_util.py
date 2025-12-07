"""
월별 환율 조회 및 저장 유틸리티

key_store.json에 환율 정보를 저장하고 불러오는 기능
- 키 형식: EXCHANGE_RATE_YYYY_MM (예: EXCHANGE_RATE_2025_12)
- yfinance로 과거 환율 자동 조회 (KRW=X 티커)
"""
from datetime import datetime, timedelta
from typing import Optional
import config.key_store as key_store


def _fetch_monthly_rate_from_yf(year: int, month: int) -> Optional[float]:
    """
    yfinance로 특정 월의 평균 환율 조회 (KRW=X)

    Args:
        year: 연도
        month: 월

    Returns:
        float: 해당 월의 평균 종가 환율 (없으면 None)
    """
    try:
        import yfinance as yf
        from calendar import monthrange

        # 해당 월의 첫날과 마지막날
        last_day = monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"

        print(f"[ExchangeRate] Fetching USD/KRW rate from yfinance for {year}-{month:02d}...")

        # USD/KRW 환율 조회
        krw = yf.Ticker("KRW=X")
        hist = krw.history(start=start_date, end=end_date)

        if hist.empty:
            print(f"[ExchangeRate] No data from yfinance for {year}-{month:02d}")
            return None

        # 해당 월의 평균 종가 환율
        avg_rate = hist['Close'].mean()
        print(f"[ExchangeRate] Fetched average rate for {year}-{month:02d}: {avg_rate:.2f}")
        return float(avg_rate)

    except Exception as e:
        print(f"[ExchangeRate] Error fetching from yfinance: {e}")
        return None


def get_monthly_exchange_rate(year: int, month: int) -> float:
    """
    특정 년월의 환율 조회

    1. key_store에서 해당 월 환율 조회
    2. 없으면 yfinance로 과거 환율 가져오기
    3. 가져온 환율 저장
    4. yfinance 실패 시 현재 환율 사용

    Args:
        year: 연도 (예: 2025)
        month: 월 (1~12)

    Returns:
        float: 환율 (예: 1475.5)
    """
    try:
        # 1. 월별 환율 키 생성
        key = f"EXCHANGE_RATE_{year}_{month:02d}"

        # 2. key_store에서 조회
        stored_rate = key_store.read(key)

        if stored_rate is not None:
            print(f"[ExchangeRate] Using stored rate for {year}-{month:02d}: {stored_rate}")
            return float(stored_rate)

        # 3. 현재 월인 경우 현재 환율 사용
        current_year = datetime.now().year
        current_month = datetime.now().month

        if year == current_year and month == current_month:
            current_rate = key_store.read("EXCHANGE_RATE")
            if current_rate is not None:
                print(f"[ExchangeRate] Using current rate for {year}-{month:02d}: {current_rate}")
                # 현재 월 환율 저장
                key_store.write(key, current_rate)
                return float(current_rate)

        # 4. 과거 월인 경우 yfinance로 환율 가져오기
        yf_rate = _fetch_monthly_rate_from_yf(year, month)
        if yf_rate is not None:
            # 저장
            key_store.write(key, yf_rate)
            return yf_rate

        # 5. yfinance 실패 시 현재 환율 사용 (저장 안 함)
        current_rate = key_store.read("EXCHANGE_RATE")
        if current_rate is not None:
            print(f"[ExchangeRate] Using fallback current rate for {year}-{month:02d}: {current_rate} (not saved)")
            return float(current_rate)

        # 6. 기본 환율 반환 (1450원)
        print(f"[ExchangeRate] Using default rate for {year}-{month:02d}: 1450.0")
        return 1450.0

    except Exception as e:
        print(f"[ExchangeRate] Error getting exchange rate for {year}-{month:02d}: {e}")
        return 1450.0  # 기본값


def set_monthly_exchange_rate(year: int, month: int, rate: float) -> bool:
    """
    특정 년월의 환율 저장

    Args:
        year: 연도
        month: 월
        rate: 환율

    Returns:
        bool: 성공 여부
    """
    try:
        key = f"EXCHANGE_RATE_{year}_{month:02d}"
        key_store.write(key, rate)
        print(f"[ExchangeRate] Saved rate for {year}-{month:02d}: {rate}")
        return True
    except Exception as e:
        print(f"[ExchangeRate] Error saving exchange rate: {e}")
        return False


def get_current_exchange_rate() -> float:
    """
    현재 환율 조회

    Returns:
        float: 현재 환율
    """
    try:
        current_rate = key_store.read("EXCHANGE_RATE")
        if current_rate is not None:
            return float(current_rate)
        return 1450.0
    except Exception as e:
        print(f"[ExchangeRate] Error getting current exchange rate: {e}")
        return 1450.0
