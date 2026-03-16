"""
Migration: bot_info 테이블에서 dynamic_seed 관련 컬럼 5개 제거

제거 대상:
- dynamic_seed_max
- dynamic_seed_enabled
- dynamic_seed_multiplier
- dynamic_seed_t_threshold
- dynamic_seed_drop_rate

실행: python migrate_drop_dynamic_seed.py
"""
import sqlite3
from pathlib import Path

ADMIN_USERS = ['chan']

PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db"

COLUMNS_TO_DROP = [
    'dynamic_seed_max',
    'dynamic_seed_enabled',
    'dynamic_seed_multiplier',
    'dynamic_seed_t_threshold',
    'dynamic_seed_drop_rate',
]


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

        dropped = []
        skipped = []

        for col in COLUMNS_TO_DROP:
            if check_column_exists(cursor, 'bot_info', col):
                print(f"  🔄 {col} 컬럼 삭제 중...")
                cursor.execute(f"ALTER TABLE bot_info DROP COLUMN {col}")
                dropped.append(col)
            else:
                print(f"  ⏭️  {col} 컬럼이 없습니다. 스킵.")
                skipped.append(col)

        conn.commit()

        print(f"  ✅ 삭제 완료: {dropped}")
        if skipped:
            print(f"  ⏭️  이미 없음: {skipped}")
        return True

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_all():
    print("=" * 50)
    print("🚀 EggMoney - dynamic_seed 컬럼 제거 마이그레이션")
    print("  - dynamic_seed_max")
    print("  - dynamic_seed_enabled")
    print("  - dynamic_seed_multiplier")
    print("  - dynamic_seed_t_threshold")
    print("  - dynamic_seed_drop_rate")
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
