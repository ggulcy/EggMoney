#!/usr/bin/env python3
"""
Trading 직접 테스트 스크립트

스케줄러 없이 trading_jobs의 함수를 직접 호출하여 테스트

사용법:
    from test_trading_direct import *

    # 의존성 초기화
    init_dependencies()

    # 첫구매 테스트
    test_first_buy()
"""
import sys
from pathlib import Path
from typing import Optional, Tuple

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from presentation.scheduler.trading_jobs import TradingJobs
from presentation.scheduler.message_jobs import MessageJobs
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
import sqlite3

# 전역 변수
_trading_jobs: Optional[TradingJobs] = None
_message_jobs: Optional[MessageJobs] = None
_session_factory: Optional[SessionFactory] = None

# DB 경로
DB_PATH = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db" / "egg_chan.db"


def init_dependencies() -> Tuple[SessionFactory, TradingJobs, MessageJobs]:
    """
    의존성 초기화 (scheduler_config의 _initialize_dependencies 호출)

    Returns:
        tuple: (session_factory, trading_jobs, message_jobs)
    """
    global _trading_jobs, _message_jobs, _session_factory

    print("=" * 80)
    print("📦 의존성 초기화 중...")
    print("=" * 80)

    from presentation.scheduler.scheduler_config import _initialize_dependencies

    _session_factory, _trading_jobs, _message_jobs = _initialize_dependencies()

    print("✅ 의존성 초기화 완료!")
    print(f"   - SessionFactory: {_session_factory}")
    print(f"   - TradingJobs: {_trading_jobs}")
    print(f"   - MessageJobs: {_message_jobs}")
    print("=" * 80)
    print()

    return _session_factory, _trading_jobs, _message_jobs


def get_dependencies() -> Tuple[SessionFactory, TradingJobs, MessageJobs]:
    """
    초기화된 의존성 반환

    Returns:
        tuple: (session_factory, trading_jobs, message_jobs)
    """
    init_dependencies()
    if _trading_jobs is None:
        raise RuntimeError("먼저 init_dependencies()를 호출하세요!")

    return _session_factory, _trading_jobs, _message_jobs


def check_db_status(bot_name: str = "TQ_2"):
    """
    DB 상태 확인

    Args:
        bot_name: 확인할 봇 이름
    """
    print("=" * 80)
    print(f"📊 DB 상태 확인 - {bot_name}")
    print("=" * 80)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # BotInfo
    cursor.execute("SELECT * FROM bot_info WHERE name=?", (bot_name,))
    bot_info = cursor.fetchone()
    if bot_info:
        print(f"\n🤖 BotInfo:")
        print(f"   Name: {bot_info[0]}")
        print(f"   Symbol: {bot_info[1]}")
        print(f"   Seed: ${bot_info[2]:,.2f}")
        print(f"   Profit Rate: {bot_info[3]*100}%")
        print(f"   T_div: {bot_info[4]}")
        print(f"   Active: {bool(bot_info[6])}")
        print(f"   Added Seed: ${bot_info[10]:,.2f}")
    else:
        print(f"\n❌ BotInfo not found: {bot_name}")

    # Trade
    cursor.execute("SELECT * FROM trade WHERE name=? ORDER BY date_added", (bot_name,))
    trades = cursor.fetchall()
    print(f"\n📊 Trade ({len(trades)}개):")
    if trades:
        for trade in trades:
            print(f"   - Date: {trade[0]} | Price: ${trade[4]:,.2f} | Amount: {trade[5]} | Type: {trade[6]}")
    else:
        print("   (비어있음)")

    # Order
    cursor.execute('SELECT * FROM "order" WHERE name=?', (bot_name,))
    order = cursor.fetchone()
    print(f"\n📋 Order:")
    if order:
        print(f"   Name: {order[0]}")
        print(f"   Type: {order[4]}")
        print(f"   Progress: {order[5]}/{order[6]}")
        print(f"   Remain: ${order[7]:,.2f} / Total: ${order[8]:,.2f}")
    else:
        print("   (주문서 없음)")

    # History (최근 5개)
    cursor.execute(
        "SELECT * FROM history WHERE name=? ORDER BY sell_date DESC LIMIT 5",
        (bot_name,)
    )
    histories = cursor.fetchall()
    print(f"\n💰 History (최근 5개):")
    if histories:
        for hist in histories:
            print(f"   - {hist[1]} | {hist[2]} | Buy: ${hist[5]:,.2f} → Sell: ${hist[6]:,.2f} | Profit: ${hist[7]:,.2f} ({hist[8]*100:.1f}%)")
    else:
        print("   (내역 없음)")

    conn.close()
    print("=" * 80)


def test_first_buy_tq2():
    """
    TQ_2 봇으로 첫구매 테스트

    1. TQ_2 봇만 활성화
    2. trade_job 호출 (주문서 생성)
    3. twap_job을 TWAP_COUNT만큼 호출 (매수 실행)
    4. DB 상태 확인
    """
    print("=" * 80)
    print("🧪 첫구매 테스트 시작 (TQ_2)")
    print("=" * 80)
    print()

    _, trading_jobs, _ = get_dependencies()

    # TWAP_COUNT 가져오기
    from config import key_store
    twap_count = key_store.read(key_store.TWAP_COUNT)

    print(f"📋 설정:")
    print(f"   - 봇: TQ_2")
    print(f"   - TWAP_COUNT: {twap_count}")
    print()

    # 1단계: TQ_2만 활성화 (다른 봇 비활성화)
    print("📝 1단계: TQ_2 봇 활성화")
    print("-" * 80)
    from data.persistence.sqlalchemy.repositories import SQLAlchemyBotInfoRepository
    session = _session_factory.create_session()
    bot_repo = SQLAlchemyBotInfoRepository(session)

    # 모든 봇 비활성화
    all_bots = bot_repo.find_all()
    for bot in all_bots:
        if bot.name == 'TQ_2':
            bot.active = True
            print(f"   ✅ {bot.name}: active = True")
        else:
            bot.active = False
            print(f"   ⏸️  {bot.name}: active = False")
        bot_repo.save(bot)

    print("✅ 봇 활성화 설정 완료")
    print()

    # 2단계: trade_job 호출 (주문서 생성)
    print("📝 2단계: trade_job 호출 (주문서 생성)")
    print("-" * 80)
    trading_jobs.trade_job()
    print("✅ trade_job 완료")
    print()

    # 3단계: twap_job을 TWAP_COUNT만큼 호출
    print(f"📝 3단계: twap_job 호출 ({twap_count}회)")
    print("-" * 80)
    for i in range(twap_count):
        print(f"⏱️  twap_job #{i+1}/{twap_count} 실행 중...")
        trading_jobs.twap_job()
        print(f"✅ twap_job #{i+1}/{twap_count} 완료")
    print()

    # 4단계: DB 상태 확인
    print("📝 4단계: DB 상태 확인")
    print("-" * 80)
    check_db_status('TQ_2')

    print()
    print("=" * 80)
    print("✅ 첫구매 테스트 완료!")
    print("=" * 80)


if __name__ == '__main__':
    print("=" * 80)
    print("🧪 EggMoney Trading Direct Test")
    print("=" * 80)

    _, trading_jobs, message_jobs = get_dependencies()

    test_first_buy_tq2()

    print("=" * 80)
