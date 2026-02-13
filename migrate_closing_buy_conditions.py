"""
Migration: bot_info 테이블 변경
- closing_buy_drop_rate, closing_buy_seed_rate 컬럼 → closing_buy_conditions (JSON Text) 변환
- 기존 값을 JSON 배열로 마이그레이션

실행: python migrate_closing_buy_conditions.py
"""
import json
import sqlite3
from pathlib import Path

ADMIN_USERS = ['chan','choe','sk']

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

        # 이미 마이그레이션 완료된 경우
        if check_column_exists(cursor, 'bot_info', 'closing_buy_conditions'):
            print(f"  ✅ closing_buy_conditions 컬럼이 이미 존재합니다. 스킵.")
            return True

        # 1. 새 컬럼 추가
        print(f"  🔄 closing_buy_conditions 컬럼 추가 중...")
        cursor.execute("ALTER TABLE bot_info ADD COLUMN closing_buy_conditions TEXT NOT NULL DEFAULT '[]'")
        conn.commit()

        # 2. 기존 데이터 마이그레이션
        has_old_columns = (
            check_column_exists(cursor, 'bot_info', 'closing_buy_drop_rate') and
            check_column_exists(cursor, 'bot_info', 'closing_buy_seed_rate')
        )

        if has_old_columns:
            print(f"  🔄 기존 데이터를 JSON으로 변환 중...")
            cursor.execute("SELECT name, closing_buy_drop_rate, closing_buy_seed_rate FROM bot_info")
            rows = cursor.fetchall()
            for name, drop_rate, seed_rate in rows:
                conditions = json.dumps([{"drop_rate": drop_rate, "seed_rate": seed_rate}])
                cursor.execute("UPDATE bot_info SET closing_buy_conditions = ? WHERE name = ?", (conditions, name))
            conn.commit()

            # 3. 기존 컬럼 삭제
            print(f"  🔄 closing_buy_drop_rate 컬럼 삭제 중...")
            cursor.execute("ALTER TABLE bot_info DROP COLUMN closing_buy_drop_rate")
            print(f"  🔄 closing_buy_seed_rate 컬럼 삭제 중...")
            cursor.execute("ALTER TABLE bot_info DROP COLUMN closing_buy_seed_rate")
            conn.commit()

        # 결과 확인
        cursor.execute("SELECT name, closing_buy_conditions FROM bot_info")
        rows = cursor.fetchall()
        print(f"  📊 현재 bot_info 데이터 ({len(rows)}개):")
        for name, conditions in rows:
            print(f"     - {name}: {conditions}")

        print(f"  ✅ 마이그레이션 완료")
        return True

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_all():
    print("=" * 50)
    print("🚀 EggMoney - closing_buy_conditions 마이그레이션")
    print("  - closing_buy_drop_rate + closing_buy_seed_rate → closing_buy_conditions (JSON)")
    print("=" * 50)

    results = {}
    for admin, db_path in get_db_paths():
        results[admin] = migrate_single_db(admin, db_path)

    print("\n" + "=" * 50)
    print("📋 마이그레이션 결과 요약")
    for admin, success in results.items():
        status = "✅ 성공" if success else "❌ 실패/스킵"
        print(f"   {admin}: {status}")
    print("=" * 50)


if __name__ == '__main__':
    migrate_all()
