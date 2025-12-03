"""
egg 프로젝트의 5개 DB 파일의 데이터를
EggMoney 프로젝트의 egg_[admin].db로 통합하는 스크립트

기존 egg 구조:
- bot_info_[admin].db (bot_info 테이블)
- trade_[admin].db (trade 테이블)
- order_[admin].db (trade 테이블 - tablename 오류)
- history_[admin].db (history 테이블)
- status_[admin].db (status 테이블)

새로운 EggMoney 구조:
- egg_[admin].db (bot_info, trade, order, history, status 5개 테이블)

사용법:
    python migrate_from_egg.py [admin]

예시:
    python migrate_from_egg.py chan
    python migrate_from_egg.py choe
    python migrate_from_egg.py sk
"""
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime


admin = "chan"


# 프로젝트 경로 설정
egg_project_path = Path(__file__).parent.parent / "egg" / "repository" / "db"
bot_info_src_db_path = egg_project_path / f"bot_info_{admin}.db"
trade_src_db_path = egg_project_path / f"trade_{admin}.db"
order_src_db_path = egg_project_path / f"order_{admin}.db"
history_src_db_path = egg_project_path / f"history_{admin}.db"
status_src_db_path = egg_project_path / f"status_{admin}.db"

target_project_path = Path(__file__).parent / "data" / "persistence" / "sqlalchemy" / "db"
target_db_path = target_project_path / f"egg_{admin}.db"

print("=" * 80)
print(f"🔄 egg 프로젝트 DB 통합 시작 (admin: {admin})")
print("=" * 80)

# 소스 DB 파일 확인
db_files = [
    ("BotInfo", bot_info_src_db_path),
    ("Trade", trade_src_db_path),
    ("Order", order_src_db_path),
    ("History", history_src_db_path),
    ("Status", status_src_db_path)
]

missing_files = []
for name, path in db_files:
    if not path.exists():
        missing_files.append(f"   ❌ {name} DB: {path}")
    else:
        print(f"   ✅ {name} DB: {path}")

if missing_files:
    print("\n⚠️  일부 DB 파일을 찾을 수 없습니다:")
    for msg in missing_files:
        print(msg)
    print("\n존재하는 파일만 마이그레이션을 계속합니다...")

print(f"\n✅ 대상 DB: {target_db_path}")
print()

# 대상 디렉토리 생성
target_project_path.mkdir(parents=True, exist_ok=True)

# 기존 파일 백업
if target_db_path.exists():
    backup_path = target_db_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    os.rename(target_db_path, backup_path)
    print(f"📦 기존 egg_{admin}.db를 백업했습니다: {backup_path.name}")

# 새로운 egg_{admin}.db 생성
print(f"\n📝 새로운 egg_{admin}.db 생성 중...")
conn = sqlite3.connect(str(target_db_path))
cursor = conn.cursor()

# 1. BotInfo 테이블 생성
print("   - BotInfo 테이블 생성...")
cursor.execute("""
    CREATE TABLE bot_info (
        name VARCHAR NOT NULL PRIMARY KEY,
        symbol VARCHAR NOT NULL,
        seed FLOAT NOT NULL,
        profit_rate FLOAT NOT NULL,
        t_div INTEGER NOT NULL,
        max_tier INTEGER NOT NULL,
        active BOOLEAN NOT NULL DEFAULT 0,
        is_check_buy_avr_price BOOLEAN NOT NULL DEFAULT 1,
        is_check_buy_t_div_price BOOLEAN NOT NULL DEFAULT 1,
        point_loc VARCHAR NOT NULL,
        added_seed FLOAT NOT NULL DEFAULT 0.0,
        skip_sell BOOLEAN NOT NULL DEFAULT 0
    )
""")

# 2. Trade 테이블 생성
print("   - Trade 테이블 생성...")
cursor.execute("""
    CREATE TABLE trade (
        date_added DATETIME NOT NULL,
        name VARCHAR NOT NULL,
        symbol VARCHAR NOT NULL,
        latest_date_trade DATETIME NOT NULL,
        purchase_price FLOAT NOT NULL,
        amount FLOAT NOT NULL,
        trade_type VARCHAR NOT NULL,
        total_price FLOAT NOT NULL,
        PRIMARY KEY (date_added, name, symbol)
    )
""")

# 3. Order 테이블 생성 (TWAP)
print("   - Order 테이블 생성...")
cursor.execute("""
    CREATE TABLE "order" (
        name VARCHAR NOT NULL PRIMARY KEY,
        date_added DATETIME NOT NULL,
        symbol VARCHAR NOT NULL,
        trade_result_list TEXT NOT NULL,
        order_type VARCHAR NOT NULL,
        trade_count INTEGER NOT NULL,
        total_count INTEGER NOT NULL,
        remain_value FLOAT NOT NULL,
        total_value FLOAT NOT NULL
    )
""")

# 4. History 테이블 생성
print("   - History 테이블 생성...")
cursor.execute("""
    CREATE TABLE history (
        date_added DATETIME NOT NULL,
        sell_date DATETIME NOT NULL,
        trade_type VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        symbol VARCHAR NOT NULL,
        buy_price FLOAT NOT NULL,
        sell_price FLOAT NOT NULL,
        profit FLOAT NOT NULL,
        profit_rate FLOAT NOT NULL,
        PRIMARY KEY (date_added, sell_date, trade_type, name)
    )
""")

# 5. Status 테이블 생성
print("   - Status 테이블 생성...")
cursor.execute("""
    CREATE TABLE status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deposit_won FLOAT NOT NULL DEFAULT 0,
        deposit_dollar FLOAT NOT NULL DEFAULT 0,
        withdraw_won FLOAT NOT NULL DEFAULT 0,
        withdraw_dollar FLOAT NOT NULL DEFAULT 0
    )
""")

conn.commit()
print("✅ 테이블 생성 완료")

# 데이터 마이그레이션
print("\n📥 데이터 마이그레이션 중...")

migration_summary = {}

# BotInfo 데이터 마이그레이션
if bot_info_src_db_path.exists():
    try:
        src_conn = sqlite3.connect(str(bot_info_src_db_path))
        src_cursor = src_conn.cursor()

        # 먼저 컬럼 확인 (is_check_buy_av_moving_price가 있는지 체크)
        src_cursor.execute("PRAGMA table_info(bot_info)")
        columns = [col[1] for col in src_cursor.fetchall()]
        has_av_moving = 'is_check_buy_av_moving_price' in columns

        if has_av_moving:
            # 기존 DB에 is_check_buy_av_moving_price가 있는 경우 (무시하고 읽음)
            src_cursor.execute("""
                SELECT name, symbol, seed, profit_rate, t_div, max_tier, active,
                       is_check_buy_avr_price, is_check_buy_t_div_price,
                       point_loc, added_seed, skip_sell
                FROM bot_info
            """)
        else:
            # 기존 DB에 없는 경우
            src_cursor.execute("""
                SELECT name, symbol, seed, profit_rate, t_div, max_tier, active,
                       is_check_buy_avr_price, is_check_buy_t_div_price,
                       point_loc, added_seed, skip_sell
                FROM bot_info
            """)

        bot_info_data = src_cursor.fetchall()

        if bot_info_data:
            print(f"   - BotInfo 데이터: {len(bot_info_data)}개 행 발견")
            for row in bot_info_data:
                cursor.execute("""
                    INSERT INTO bot_info
                    (name, symbol, seed, profit_rate, t_div, max_tier, active,
                     is_check_buy_avr_price, is_check_buy_t_div_price,
                     point_loc, added_seed, skip_sell)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.commit()
            print(f"   ✅ BotInfo 데이터 {len(bot_info_data)}개 마이그레이션 완료")
            migration_summary['BotInfo'] = len(bot_info_data)
        else:
            print("   ⚠️  BotInfo 데이터가 없습니다")
            migration_summary['BotInfo'] = 0

        src_conn.close()
    except Exception as e:
        print(f"   ❌ BotInfo 데이터 마이그레이션 실패: {str(e)}")
        migration_summary['BotInfo'] = 'ERROR'

# Trade 데이터 마이그레이션
if trade_src_db_path.exists():
    try:
        src_conn = sqlite3.connect(str(trade_src_db_path))
        src_cursor = src_conn.cursor()
        src_cursor.execute("""
            SELECT date_added, name, symbol, latest_date_trade, purchase_price, amount, trade_type, total_price
            FROM trade
        """)
        trade_data = src_cursor.fetchall()

        if trade_data:
            print(f"   - Trade 데이터: {len(trade_data)}개 행 발견")
            for row in trade_data:
                cursor.execute("""
                    INSERT INTO trade
                    (date_added, name, symbol, latest_date_trade, purchase_price, amount, trade_type, total_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.commit()
            print(f"   ✅ Trade 데이터 {len(trade_data)}개 마이그레이션 완료")
            migration_summary['Trade'] = len(trade_data)
        else:
            print("   ⚠️  Trade 데이터가 없습니다")
            migration_summary['Trade'] = 0

        src_conn.close()
    except Exception as e:
        print(f"   ❌ Trade 데이터 마이그레이션 실패: {str(e)}")
        migration_summary['Trade'] = 'ERROR'

# Order 데이터 마이그레이션 (egg에서는 tablename이 'trade'로 잘못 되어있을 수 있음)
if order_src_db_path.exists():
    try:
        src_conn = sqlite3.connect(str(order_src_db_path))
        src_cursor = src_conn.cursor()

        # 먼저 테이블 존재 확인
        src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in src_cursor.fetchall()]

        order_table_name = 'order' if 'order' in tables else 'trade'
        print(f"   - Order 소스 테이블명: {order_table_name}")

        src_cursor.execute(f"""
            SELECT name, date_added, symbol, trade_result_list, order_type,
                   trade_count, total_count, remain_value, total_value
            FROM {order_table_name}
        """)
        order_data = src_cursor.fetchall()

        if order_data:
            print(f"   - Order 데이터: {len(order_data)}개 행 발견")
            for row in order_data:
                cursor.execute("""
                    INSERT INTO "order"
                    (name, date_added, symbol, trade_result_list, order_type,
                     trade_count, total_count, remain_value, total_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.commit()
            print(f"   ✅ Order 데이터 {len(order_data)}개 마이그레이션 완료")
            migration_summary['Order'] = len(order_data)
        else:
            print("   ⚠️  Order 데이터가 없습니다")
            migration_summary['Order'] = 0

        src_conn.close()
    except Exception as e:
        print(f"   ❌ Order 데이터 마이그레이션 실패: {str(e)}")
        migration_summary['Order'] = 'ERROR'

# History 데이터 마이그레이션
if history_src_db_path.exists():
    try:
        src_conn = sqlite3.connect(str(history_src_db_path))
        src_cursor = src_conn.cursor()
        src_cursor.execute("""
            SELECT date_added, sell_date, trade_type, name, symbol,
                   buy_price, sell_price, profit, profit_rate
            FROM history
        """)
        history_data = src_cursor.fetchall()

        if history_data:
            print(f"   - History 데이터: {len(history_data)}개 행 발견")
            for row in history_data:
                cursor.execute("""
                    INSERT INTO history
                    (date_added, sell_date, trade_type, name, symbol,
                     buy_price, sell_price, profit, profit_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.commit()
            print(f"   ✅ History 데이터 {len(history_data)}개 마이그레이션 완료")
            migration_summary['History'] = len(history_data)
        else:
            print("   ⚠️  History 데이터가 없습니다")
            migration_summary['History'] = 0

        src_conn.close()
    except Exception as e:
        print(f"   ❌ History 데이터 마이그레이션 실패: {str(e)}")
        migration_summary['History'] = 'ERROR'

# Status 데이터 마이그레이션
if status_src_db_path.exists():
    try:
        src_conn = sqlite3.connect(str(status_src_db_path))
        src_cursor = src_conn.cursor()
        src_cursor.execute("""
            SELECT deposit_won, deposit_dollar, withdraw_won, withdraw_dollar
            FROM status
        """)
        status_data = src_cursor.fetchall()

        if status_data:
            print(f"   - Status 데이터: {len(status_data)}개 행 발견")
            for row in status_data:
                cursor.execute("""
                    INSERT INTO status
                    (deposit_won, deposit_dollar, withdraw_won, withdraw_dollar)
                    VALUES (?, ?, ?, ?)
                """, row)
            conn.commit()
            print(f"   ✅ Status 데이터 {len(status_data)}개 마이그레이션 완료")
            migration_summary['Status'] = len(status_data)
        else:
            print("   ⚠️  Status 데이터가 없습니다")
            migration_summary['Status'] = 0

        src_conn.close()
    except Exception as e:
        print(f"   ❌ Status 데이터 마이그레이션 실패: {str(e)}")
        migration_summary['Status'] = 'ERROR'

# 마이그레이션 완료
conn.close()

print("\n" + "=" * 80)
print("✅ 마이그레이션 완료!")
print("=" * 80)
print(f"📍 생성된 DB: {target_db_path}")
print()

# 마이그레이션된 데이터 확인
try:
    verify_conn = sqlite3.connect(str(target_db_path))
    verify_cursor = verify_conn.cursor()

    print("📊 마이그레이션 결과:")

    verify_cursor.execute("SELECT COUNT(*) FROM bot_info")
    bot_info_count = verify_cursor.fetchone()[0]
    print(f"   - BotInfo: {bot_info_count}개")

    verify_cursor.execute("SELECT COUNT(*) FROM trade")
    trade_count = verify_cursor.fetchone()[0]
    print(f"   - Trade: {trade_count}개")

    verify_cursor.execute('SELECT COUNT(*) FROM "order"')
    order_count = verify_cursor.fetchone()[0]
    print(f"   - Order: {order_count}개")

    verify_cursor.execute("SELECT COUNT(*) FROM history")
    history_count = verify_cursor.fetchone()[0]
    print(f"   - History: {history_count}개")

    verify_cursor.execute("SELECT COUNT(*) FROM status")
    status_count = verify_cursor.fetchone()[0]
    print(f"   - Status: {status_count}개")

    verify_conn.close()

    print("\n💡 다음 단계:")
    print("   1. EggMoney 프로젝트에서 session_factory.py의 DB 경로 확인")
    print(f"   2. config/item.py에서 admin 값이 '{admin}'인지 확인")
    print("   3. main_egg.py 실행하여 정상 작동 확인")

except Exception as e:
    print(f"⚠️  데이터 확인 실패: {str(e)}")
