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
load_dotenv(dotenv_path=dotenv_path, override=False)


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
    print("\n" + "=" * 80)
    print("🔍 IS_TEST 환경변수 확인 중...")
    print("=" * 80)

    test_value = os.getenv('IS_TEST')
    print(f"📌 IS_TEST 환경변수: {test_value if test_value else '(설정되지 않음)'}")

    if test_value:
        test_value_lower = test_value.lower()
        print(f"✅ 환경변수에서 읽은 값: '{test_value}' (소문자: '{test_value_lower}')")

        if test_value_lower == 'false':
            print(f"✅ IS_TEST 설정: False (프로덕션 모드)")
            print("=" * 80 + "\n")
            return False
        else:
            print(f"✅ IS_TEST 설정: True ('{test_value}'는 False가 아님)")
            print("=" * 80 + "\n")
            return True

    print("⚠️  IS_TEST 환경변수가 설정되지 않음 → 기본값: True (테스트 모드)")
    print("=" * 80 + "\n")
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
        print(f"✅ 환경변수에서 읽은 값: '{admin_value}' (소문자: '{admin_value_lower}')")

        if admin_value_lower == 'chan':
            print(f"✅ ADMIN 설정: Chan (환경변수에서 읽음)")
            print("=" * 80 + "\n")
            return BotAdmin.Chan
        elif admin_value_lower == 'choe':
            print(f"✅ ADMIN 설정: Choe (환경변수에서 읽음)")
            print("=" * 80 + "\n")
            return BotAdmin.Choe
        elif admin_value_lower == 'sk':
            print(f"✅ ADMIN 설정: SK (환경변수에서 읽음)")
            print("=" * 80 + "\n")
            return BotAdmin.SK
        else:
            print(f"⚠️  알 수 없는 ADMIN 값: '{admin_value}' → 기본값: Chan")
            print("=" * 80 + "\n")
            return BotAdmin.Chan

    print("⚠️  ADMIN 환경변수가 설정되지 않음 → 기본값: None")
    print("=" * 80 + "\n")
    return None


admin = _get_admin_from_env()


# 테스트용 가격 설정 (egg 프로젝트 호환)
test_buy_prev_price = 53
test_price = 300
test_sell_price = test_price
