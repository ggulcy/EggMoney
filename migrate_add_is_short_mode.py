"""
Migration: bot_info 테이블에 is_short_mode 컬럼 추가
실행: python migrate_add_is_short_mode.py
"""
import sqlite3
import os
from pathlib import Path

# 관리자 목록 (하드코딩)
ADMIN_USERS = ['chan','choe','sk']

# DB 디렉토리 경로 (프로젝트 루트 기준)
PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db"


def get_db_paths():
    """모든 관리자의 DB 경로 목록 반환"""
    paths = []
    for admin in ADMIN_USERS:
        db_path = DB_DIR / f"egg_{admin}.db"
        paths.append((admin, db_path))
    return paths


def check_column_exists(cursor, table_name, column_name):
    """컬럼 존재 여부 확인"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_single_db(admin, db_path):
    """단일 DB에 대한 마이그레이션 수행"""
    print(f"\n{'─' * 40}")
    print(f"👤 {admin.upper()} DB 마이그레이션")
    print(f"📂 경로: {db_path}")

    if not db_path.exists():
        print(f"⚠️  DB 파일이 존재하지 않습니다. 스킵합니다.")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # bot_info 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_info'")
        if not cursor.fetchone():
            print(f"⚠️  bot_info 테이블이 존재하지 않습니다. 스킵합니다.")
            return False

        # 컬럼 존재 여부 확인
        if check_column_exists(cursor, 'bot_info', 'is_short_mode'):
            print("✅ is_short_mode 컬럼이 이미 존재합니다.")
            return True

        # 컬럼 추가
        print("🔄 is_short_mode 컬럼 추가 중...")
        cursor.execute("""
            ALTER TABLE bot_info
            ADD COLUMN is_short_mode BOOLEAN NOT NULL DEFAULT 0
        """)

        conn.commit()
        print("✅ 마이그레이션 완료!")

        # 확인
        cursor.execute("SELECT name, is_short_mode FROM bot_info")
        rows = cursor.fetchall()
        print(f"📊 현재 bot_info 데이터 ({len(rows)}개):")
        for row in rows:
            print(f"   - {row[0]}: is_short_mode = {bool(row[1])}")

        return True

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_all():
    """모든 관리자 DB에 대해 마이그레이션 수행"""
    print("=" * 50)
    print("🚀 EggMoney - is_short_mode 컬럼 마이그레이션")
    print("=" * 50)
    print(f"📁 DB 디렉토리: {DB_DIR}")
    print(f"👥 대상 관리자: {', '.join(ADMIN_USERS)}")

    results = {}
    for admin, db_path in get_db_paths():
        results[admin] = migrate_single_db(admin, db_path)

    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 마이그레이션 결과 요약")
    print("=" * 50)
    for admin, success in results.items():
        status = "✅ 성공" if success else "❌ 실패/스킵"
        print(f"   {admin}: {status}")
    print("=" * 50)


if __name__ == '__main__':
    migrate_all()
