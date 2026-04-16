"""
Migration: bot_info 테이블에 trailing stop 관련 컬럼 추가

추가 컬럼:
  - trailing_enabled       BOOLEAN DEFAULT 0
  - trailing_t_threshold   FLOAT   DEFAULT 0.3  (max_tier 대비 비율, 0.3=30%)
  - trailing_atr_multiplier FLOAT  DEFAULT 1.0
  - trailing_floor_rate    FLOAT   DEFAULT 0.10
  - trailing_mode          BOOLEAN DEFAULT 0
  - trailing_high_watermark FLOAT  DEFAULT 0.0
  - trailing_stop          FLOAT   DEFAULT 0.0

실행: python migrate_add_trailing_stop.py
"""
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env', override=True)

DB_DIR = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db"

NEW_COLUMNS = [
    ("trailing_enabled",        "BOOLEAN", "0"),
    ("trailing_t_threshold",    "FLOAT",   "0.3"),
    ("trailing_atr_multiplier", "FLOAT",   "1.0"),
    ("trailing_floor_rate",     "FLOAT",   "0.10"),
    ("trailing_mode",           "BOOLEAN", "0"),
    ("trailing_high_watermark", "FLOAT",   "0.0"),
    ("trailing_stop",           "FLOAT",   "0.0"),
]


def _get_admin_users() -> list[str]:
    admin = os.getenv('ADMIN', '').strip().lower()
    if not admin:
        raise ValueError("ADMIN 환경변수가 설정되지 않았습니다.")
    return [admin]


def get_db_paths():
    paths = []
    for admin in _get_admin_users():
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

        for col_name, col_type, col_default in NEW_COLUMNS:
            if check_column_exists(cursor, 'bot_info', col_name):
                print(f"  ⏭️  {col_name} 이미 존재합니다. 스킵.")
            else:
                print(f"  🔄 {col_name} 컬럼 추가 중...")
                cursor.execute(
                    f"ALTER TABLE bot_info ADD COLUMN {col_name} {col_type} NOT NULL DEFAULT {col_default}"
                )
                print(f"  ✅ 추가 완료: {col_name} ({col_type}, default={col_default})")

        conn.commit()
        return True

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_all():
    print("=" * 50)
    print("🚀 EggMoney - trailing stop 컬럼 추가 마이그레이션")
    print("=" * 50)
    admin_users = _get_admin_users()
    print(f"📁 DB 디렉토리: {DB_DIR}")
    print(f"👥 대상 관리자: {', '.join(admin_users)}")

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
