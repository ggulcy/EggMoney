"""공통 유틸리티 함수 모음"""
import json
import time
from datetime import datetime, timedelta
from typing import List

import pytz
import requests
from bs4 import BeautifulSoup

from config import item
from config.key_store import read, write
from domain.value_objects.point_loc import PointLoc


def is_trade_date():
    """오늘이 거래일인지 확인 (미국 주식 기준 - NYSE 캘린더 사용, 한국 시간 기준)"""
    import pandas_market_calendars as mcal

    nyse = mcal.get_calendar('NYSE')
    today_kst = datetime.today()

    # 한국 시간 기준 어제 = 미국 시간 기준 오늘
    # (한국 화요일 새벽 = 미국 월요일 장)
    us_date = (today_kst - timedelta(days=1)).strftime('%Y-%m-%d')

    schedule = nyse.schedule(start_date=us_date, end_date=us_date)
    is_open = len(schedule) > 0

    return is_open

# === 날짜/시간 유틸 ===
def get_msg_times():
    """서머타임을 고려한 메시지 전송 시간 반환"""
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz)

    if now_ny.dst().total_seconds() != 0:
        # 서머타임 적용 중
        return ["05:00"]
    else:
        # 서머타임 비적용
        return ["06:00"]


def get_twap_times():
    """서머타임을 고려한 TWAP 시작/종료 시간 반환 (미국 장 종료 30분 전까지)"""
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz)

    if now_ny.dst().total_seconds() != 0:
        # 서머타임 적용 중
        # TWAP 종료: 15:30 ET → 한국 시간 04:30 (다음날)
        return ["00:10", "04:30"]
    else:
        # 서머타임 비적용
        # TWAP 종료: 15:30 ET → 한국 시간 05:30 (다음날)
        return ["00:10", "05:30"]


def get_previous_date(n):
    """n일 전 날짜를 YYYYMMDD 형식으로 반환"""
    today = datetime.now()
    previous_date = today - timedelta(days=n)
    return previous_date.strftime('%Y%m%d')


def get_time_timeline(start_time: str, end_time: str, count: int) -> List[str]:
    # """
    # 시작 시간과 끝 시간, 분할 개수를 입력받아 균등하게 분할된 시간 리스트를 반환합니다.
    #
    # Args:
    #     start_time: 시작 시간 (예: "01:00")
    #     end_time: 끝 시간 (예: "05:00")
    #     count: 분할 개수 (시작과 끝을 포함한 총 개수)
    #
    # Returns:
    #     시간 문자열 리스트 (예: ["01:00", "02:00", "03:00", "04:00", "05:00"])
    #
    # Example:
    #     >>> get_time_timeline("01:00", "05:00", 5)
    #     ["01:00", "02:00", "03:00", "04:00", "05:00"]
    # """
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")

    # 끝 시간이 시작 시간보다 이전이면 다음날로 간주
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    total_duration = end_dt - start_dt

    # 분할 간격 계산
    if count <= 1:
        return [start_time]

    interval = total_duration / (count - 1)

    # 시간 리스트 생성
    timeline = []
    for i in range(count):
        current_time = start_dt + (interval * i)
        timeline.append(current_time.strftime("%H:%M"))

    return timeline


def clean_old_dates(retain_days: int = 10):
    """
    티커별 저장된 YF_DATA_DATE 중 오래된 항목을 삭제합니다.
    retain_days: 최근 유지할 날짜 수 (기본 10일)
    """
    from config.key_store import get_all_keys, delete
    threshold = datetime.today().date() - timedelta(days=retain_days)
    removed_keys = []

    for key in get_all_keys():
        if key.endswith('_YF_DATA_DATE'):
            try:
                saved_date = datetime.strptime(read(key), '%Y-%m-%d').date()
                if saved_date < threshold:
                    delete(key)
                    removed_keys.append(key)
            except Exception as e:
                print(f"⚠️ 날짜 파싱 실패: {key} → {e}")

    print(f"🧹 삭제된 키 목록 ({len(removed_keys)}개): {removed_keys}")


# === 거래 계산 ===
def get_profit_rate(cur_price, purchase_price):
    """수익률 계산"""
    if cur_price is None or purchase_price is None:
        return 0
    else:
        return round(((cur_price - purchase_price) / purchase_price) * 100, 2)

def get_buy_amount(seed: float, price: float):
    """매수 가능 수량 계산"""
    return int(seed / price)


def get_T(total: float, seed: float):
    """티어 계산"""
    t_value = round(total / seed, 2)
    return t_value


def get_point_loc(div_value: float, max_tier: int, t: float, point_loc: PointLoc) -> float:
    """포인트 위치에 따른 손절 가격 계산"""
    # div_value → 소수점으로 변환 (20 → 0.2)
    div_value = div_value / 100

    if point_loc == PointLoc.P1:
        return div_value * (1 - t / max_tier)

    elif point_loc == PointLoc.P1_2:
        if t <= max_tier / 2:
            return div_value * (1 - 2 * t / max_tier)
        else:
            return -div_value * (2 * t / max_tier - 1)

    elif point_loc == PointLoc.P2_3:
        two_third = max_tier * 2 / 3
        if t <= two_third:
            return div_value * (1 - t / two_third)
        else:
            return -div_value * (t - two_third) / (max_tier - two_third)

    else:
        raise ValueError(f"Invalid point_loc: {point_loc}")


# === 포맷팅 ===
def get_json_format(json_str):
    """JSON을 예쁘게 포맷팅"""
    return json.dumps(json_str, indent=4)


def create_progress_bar(rate: float, blocks: int = 10) -> str:
    """
    비율(%)에 따라 진행 바 색상을 다르게 출력
    - 50 이하: 🟩⬜
    - 50 초과: 🟥⬜
    """
    capped_rate = min(rate, 100.0)
    filled = int(capped_rate // (100 / blocks))
    empty = blocks - filled

    if rate <= 50:
        fill_block = '🟩'
    else:
        fill_block = '🟥'

    bar = ' '.join([fill_block] * filled + ['⬜'] * empty)
    return f"{bar}"


def get_ox_emoji(flag: bool) -> str:
    """bool 값을 이모지로 변환"""
    if flag:
        return "⭕️"
    else:
        return "❌"


def get_point_loc_text(point_loc: PointLoc) -> str:
    """PointLoc을 한글 텍스트로 변환"""
    if point_loc is PointLoc.P1:
        return "손절없음"
    elif point_loc is PointLoc.P1_2:
        return "1/2지점"
    elif point_loc is PointLoc.P2_3:
        return "2/3지점"
    return None


# === 비즈니스 로직 ===
def check_bot_name(names: List[str]):
    """현재 admin이 주어진 이름 목록에 포함되는지 확인"""
    if item.admin.value in names:
        return True
    else:
        return False


# === 환율 조회 ===
EXCHANGE_RATE_KEY = "EXCHANGE_RATE"
EXCHANGE_RATE_TIME_KEY = "EXCHANGE_RATE_TIME"


def get_naver_exchange_rate() -> float:
    """
    네이버 금융에서 USD/KRW 환율을 가져오며,
    5분 이내 요청은 캐시 데이터를 사용합니다.

    Returns:
        float: USD/KRW 환율
    """
    current_time = time.time()
    last_request_time = read(EXCHANGE_RATE_TIME_KEY)

    # 5분(300초) 이내면 캐시 사용
    if last_request_time is not None and (current_time - last_request_time) < 300:
        cached = read(EXCHANGE_RATE_KEY)
        if cached is not None:
            return cached

    try:
        url = "https://finance.naver.com/marketindex/"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        exchange_rate = soup.select_one("div.head_info > span.value").text.replace(",", "")
        rate = float(exchange_rate)

        # 캐시 저장
        write(EXCHANGE_RATE_KEY, rate)
        write(EXCHANGE_RATE_TIME_KEY, current_time)

        return rate

    except Exception as e:
        print(f"환율 데이터를 가져오는 중 오류 발생: {e}")
        return 0.0


# === 스케줄러 시간 설정 ===
def get_schedule_times() -> tuple:
    """
    스케줄러에 필요한 모든 시간 설정을 반환합니다.
    config_store 또는 기본값 사용.

    Returns:
        (job_times, msg_times, twap_times)
    """
    from config import key_store

    # msg_times: 메시지 전송 시간
    msg_times = get_msg_times()

    # job_times: 메인 거래 시간
    try:
        job_times = [key_store.read(key_store.TRADE_TIME)]
    except Exception:
        job_times = ['04:35']  # 기본값

    # twap_times: TWAP 주문 실행 시간들
    try:
        twap_time_table = key_store.read(key_store.TWAP_TIME)
        twap_count = key_store.read(key_store.TWAP_COUNT)
        twap_times = get_time_timeline(
            start_time=twap_time_table[0],
            end_time=twap_time_table[1],
            count=twap_count
        )
    except Exception:
        twap_times = get_time_timeline(
            start_time='04:35',
            end_time='04:50',
            count=5
        )

    print(f"📅 Schedule times:")
    print(f"  - msg_times: {msg_times}")
    print(f"  - job_times: {job_times}")
    print(f"  - twap_times: {twap_times}")

    return job_times, msg_times, twap_times


# === 월별 환율 조회 ===
def _fetch_monthly_rate_from_yf(year: int, month: int):
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
        stored_rate = read(key)

        if stored_rate is not None:
            return float(stored_rate)

        # 3. 현재 월인 경우 현재 환율 사용
        current_year = datetime.now().year
        current_month = datetime.now().month

        if year == current_year and month == current_month:
            current_rate = read(EXCHANGE_RATE_KEY)
            if current_rate is not None:
                print(f"[ExchangeRate] Using current rate for {year}-{month:02d}: {current_rate}")
                # 현재 월 환율 저장
                write(key, current_rate)
                return float(current_rate)

        # 4. 과거 월인 경우 yfinance로 환율 가져오기
        yf_rate = _fetch_monthly_rate_from_yf(year, month)
        if yf_rate is not None:
            # 저장
            write(key, yf_rate)
            return yf_rate

        # 5. yfinance 실패 시 현재 환율 사용 (저장 안 함)
        current_rate = read(EXCHANGE_RATE_KEY)
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
        write(key, rate)
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
        current_rate = read(EXCHANGE_RATE_KEY)
        if current_rate is not None:
            return float(current_rate)
        return 1450.0
    except Exception as e:
        print(f"[ExchangeRate] Error getting current exchange rate: {e}")
        return 1450.0


# === 시드 비율 계산 ===
def get_seed_ratio_by_drawdown(
    drawdown_rate: float,
    interval_rate: float,
    max_count: int
) -> float:
    """
    고점 대비 하락률에 따른 시드 투입 비율 계산

    Args:
        drawdown_rate: 현재 고점 대비 하락률 (소수, 음수, 예: -0.12)
        interval_rate: 하락률 인터벌 (소수, 예: 0.03)
        max_count: 최대 하락 카운트 횟수 (예: 5)

    Returns:
        float: 시드 비율 (0.0 ~ 1.0)

    Example:
        >>> get_seed_ratio_by_drawdown(-0.12, 0.03, 5)  # 12% / 3% = 4카운트, 4/5 = 0.8
        0.8
    """
    if interval_rate <= 0 or max_count <= 0:
        return 0.0

    # 하락률을 양수로 변환
    abs_drawdown = abs(drawdown_rate)

    # 하락 카운트 계산 (반올림 - 부동소수점 오차 방지)
    drop_count = round(abs_drawdown / interval_rate)

    # 최대 카운트 제한
    drop_count = min(drop_count, max_count)

    # 시드 비율 반환
    return drop_count / max_count


# === 파일시스템 관리 ===
def remove_empty_directories(root_path: str, dry_run: bool = True) -> List[str]:
    """
    프로젝트 루트부터 시작해서 빈 디렉토리를 재귀적으로 삭제합니다.

    Args:
        root_path: 검색을 시작할 루트 경로
        dry_run: True이면 삭제 예정 목록만 반환, False이면 실제 삭제 수행

    Returns:
        List[str]: 삭제된(또는 삭제 예정인) 디렉토리 경로 목록

    Example:
        >>> # 삭제 예정 목록만 확인
        >>> removed = remove_empty_directories('/path/to/project', dry_run=True)
        >>> # 실제 삭제 수행
        >>> removed = remove_empty_directories('/path/to/project', dry_run=False)
    """
    import os
    import shutil

    removed_dirs = []

    # 특정 디렉토리는 제외 (venv, .git, __pycache__ 등)
    exclude_dirs = {'.git', '.idea', '__pycache__', 'venv', '.venv', 'node_modules', '.DS_Store'}

    def is_empty_dir(dir_path: str) -> bool:
        """디렉토리가 비어있는지 확인 (숨김파일 제외)"""
        try:
            entries = os.listdir(dir_path)
            # .DS_Store 같은 숨김파일만 있으면 빈 것으로 간주
            visible_entries = [e for e in entries if not e.startswith('.')]
            return len(visible_entries) == 0
        except PermissionError:
            return False

    # 하위 디렉토리부터 상위로 올라가며 처리 (bottom-up)
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        # 제외 디렉토리 필터링
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        # 현재 디렉토리가 비어있는지 확인
        if is_empty_dir(dirpath) and dirpath != root_path:
            removed_dirs.append(dirpath)
            if not dry_run:
                try:
                    shutil.rmtree(dirpath)
                    print(f"🗑️  삭제됨: {dirpath}")
                except Exception as e:
                    print(f"⚠️  삭제 실패: {dirpath} → {e}")

    return removed_dirs

