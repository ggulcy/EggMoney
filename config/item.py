"""전역 상수 및 설정"""
import enum
import os
from enum import Enum


class BotAdmin(enum.Enum):
    """봇 관리자 (사용자 구분)"""
    Chan = 'chan'
    Choe = 'choe'
    SK = 'sk'


def _get_admin_from_env():
    """
    환경변수에서 admin 값을 읽어옴

    환경변수 우선순위:
    1. EGGMONEY_ADMIN
    2. BOT_ADMIN

    Returns:
        BotAdmin: 관리자 Enum (기본값: Chan)
    """
    admin_value = os.getenv('ADMIN') or os.getenv('BOT_ADMIN')

    if admin_value:
        admin_value = admin_value.lower()
        if admin_value == 'chan':
            return BotAdmin.Chan
        elif admin_value == 'choe':
            return BotAdmin.Choe
        elif admin_value == 'sk':
            return BotAdmin.SK
        else:
            return None

    return None


# 현재 사용 중인 관리자
# None으로 설정하면 환경변수에서 읽음 (EGGMONEY_ADMIN 또는 BOT_ADMIN)
# 직접 설정: admin = BotAdmin.Chan
admin = None

if admin is None:
    admin = _get_admin_from_env()
    print(f"✅ Admin 설정: {admin.value} (환경변수에서 읽음)")


# 테스트 모드 플래그 (egg 프로젝트 호환)
is_test = True
test_buy_prev_price = 53
test_price = 300
test_sell_price = test_price
