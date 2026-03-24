"""
Migration: bot_info 테이블에 sell_cooldown_days, sell_cooldown_loss_only 컬럼 추가
실행: python migrate_add_sell_cooldown.py
"""
import sqlite3
from pathlib import Path

ADMIN_USERS = ['sk']

PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db"


def get_db_paths():
    paths = []
    for admin in ADMIN_USERS:
        db_path = DB_DIR / f"egg_{admin}.db"
        paths.append((admin, db_path))
    return paths


def check_column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_single_db(admin, db_path):
    print(f"\n{'─' * 40}")
    print(f"👤 {admin.upper()} DB 마이그레이션")
    print(f"📂 경로: {db_path}")

    if not db_path.exists():
        print(f"⚠️  DB 파일이 존재하지 않습니다. 스킵합니다.")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_info'")
        if not cursor.fetchone():
            print(f"⚠️  bot_info 테이블이 존재하지 않습니다. 스킵합니다.")
            return False

        added = []

        if not check_column_exists(cursor, 'bot_info', 'sell_cooldown_days'):
            cursor.execute("ALTER TABLE bot_info ADD COLUMN sell_cooldown_days INTEGER NOT NULL DEFAULT 0")
            added.append('sell_cooldown_days')
        else:
            print("✅ sell_cooldown_days 컬럼이 이미 존재합니다.")

        if not check_column_exists(cursor, 'bot_info', 'sell_cooldown_loss_only'):
            cursor.execute("ALTER TABLE bot_info ADD COLUMN sell_cooldown_loss_only BOOLEAN NOT NULL DEFAULT 0")
            added.append('sell_cooldown_loss_only')
        else:
            print("✅ sell_cooldown_loss_only 컬럼이 이미 존재합니다.")

        conn.commit()

        if added:
            print(f"✅ 컬럼 추가 완료: {', '.join(added)}")

        cursor.execute("SELECT name, sell_cooldown_days, sell_cooldown_loss_only FROM bot_info")
        rows = cursor.fetchall()
        print(f"📊 현재 bot_info 데이터 ({len(rows)}개):")
        for row in rows:
            print(f"   - {row[0]}: cooldown_days={row[1]}, loss_only={bool(row[2])}")

        return True

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_all():
    print("=" * 50)
    print("🚀 EggMoney - sell_cooldown 컬럼 마이그레이션")
    print("=" * 50)

    results = {}
    for admin, db_path in get_db_paths():
        results[admin] = migrate_single_db(admin, db_path)

    print("\n" + "=" * 50)
    print("📋 마이그레이션 결과 요약")
    print("=" * 50)
    for admin, success in results.items():
        status = "✅ 성공" if success else "❌ 실패/스킵"
        print(f"   {admin}: {status}")
    print("=" * 50)


if __name__ == '__main__':
    migrate_all()
