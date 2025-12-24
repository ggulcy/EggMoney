"""전역 상수 및 설정"""
import enum
import os
from enum import Enum
from pathlib import Path

# .env 파일 로드 (config/item.py가 import될 때 자동 로드)
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)


class BotAdmin(enum.Enum):
    """봇 관리자 (사용자 구분)"""
    Chan = 'chan'
    Choe = 'choe'
    SK = 'sk'


def _get_is_test_from_env():
    """
    환경변수에서 IS_TEST 값을 읽어옴

    Returns:
        bool: 테스트 모드 여부 (기본값: True)
    """

    test_value = os.getenv('IS_TEST')
    print(f"📌 IS_TEST 환경변수: {test_value if test_value else '(설정되지 않음)'}")

    if test_value:
        test_value_lower = test_value.lower()

        if test_value_lower == 'false':
            return False
        else:
            return True

    return True


is_test = _get_is_test_from_env()


def _get_admin_from_env():
    """
    환경변수에서 admin 값을 읽어옴

    환경변수 우선순위:
    1. ADMIN

    Returns:
        BotAdmin: 관리자 Enum (기본값: None)
    """
    print("\n" + "=" * 80)
    print("🔍 ADMIN 환경변수 확인 중...")
    print("=" * 80)

    admin_value = os.getenv('ADMIN')
    print(f"📌 ADMIN 환경변수: {admin_value if admin_value else '(설정되지 않음)'}")

    if admin_value:
        admin_value_lower = admin_value.lower()

        if admin_value_lower == 'chan':
            return BotAdmin.Chan
        elif admin_value_lower == 'choe':
            return BotAdmin.Choe
        elif admin_value_lower == 'sk':
            return BotAdmin.SK
        else:
            return BotAdmin.Chan

    return None


admin = _get_admin_from_env()


# 테스트용 가격 설정 (egg 프로젝트 호환)
test_buy_prev_price = 53
test_price = 300
test_sell_price = test_price


# === 티커별 하락률 인터벌 설정 ===
# TQQQ: 변동성 낮음 → 3%
# 그 외 (SOXL 등): 변동성 높음 → 5%
TICKER_DROP_INTERVAL = {
    "TQQQ": 0.03,
}
DEFAULT_DROP_INTERVAL = 0.05


def get_drop_interval_rate(symbol: str) -> float:
    """
    티커별 하락률 인터벌 반환 (소수)

    Args:
        symbol: 티커 심볼 (예: TQQQ, SOXL)

    Returns:
        float: 하락률 인터벌 (예: 0.03 → 3%)
    """
    return TICKER_DROP_INTERVAL.get(symbol, DEFAULT_DROP_INTERVAL)
