"""
BotInfo 테이블 스키마 마이그레이션 스크립트

변경 사항:
- dynamic_seed_max 컬럼 추가 (기본값: 0.0, 기능 비활성화)

사용법:
    python migrate_bot_info_dynamic_seed.py

admin은 스크립트 내에서 하드코딩으로 변경
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


def migrate_bot_info():
    """BotInfo 테이블에 dynamic_seed_max 컬럼 추가"""

    # ===== 여기서 admin 변경 =====
    admin = "chan"  # chan, choe, sk 중 선택
    # =============================

    # DB 경로 설정
    db_path = Path(__file__).parent / "data" / "persistence" / "sqlalchemy" / "db" / f"egg_{admin}.db"

    print("=" * 80)
    print(f"🔄 BotInfo 테이블 dynamic_seed_max 컬럼 추가 (admin: {admin})")
    print("=" * 80)

    if not db_path.exists():
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return False

    print(f"📍 대상 DB: {db_path}")

    # 백업 생성
    backup_path = db_path.with_suffix(f".backup_botinfo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy(db_path, backup_path)
    print(f"📦 백업 생성: {backup_path.name}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 현재 테이블 구조 확인
        print("\n📥 현재 bot_info 테이블 구조 확인...")
        cursor.execute("PRAGMA table_info(bot_info)")
        columns = {col[1]: col for col in cursor.fetchall()}
        print(f"   - 현재 컬럼: {list(columns.keys())}")

        # 2. dynamic_seed_max 컬럼 존재 여부 확인
        if 'dynamic_seed_max' in columns:
            print("   ⚠️  dynamic_seed_max 컬럼이 이미 존재합니다. 마이그레이션 스킵.")
            return True

        # 3. 컬럼 추가
        print("\n📝 dynamic_seed_max 컬럼 추가 중...")
        cursor.execute("""
            ALTER TABLE bot_info
            ADD COLUMN dynamic_seed_max FLOAT NOT NULL DEFAULT 0.0
        """)
        conn.commit()

        # 4. 검증
        print("\n🔍 마이그레이션 검증...")
        cursor.execute("PRAGMA table_info(bot_info)")
        new_columns = [col[1] for col in cursor.fetchall()]
        print(f"   - 새 컬럼 목록: {new_columns}")

        if 'dynamic_seed_max' in new_columns:
            print("   ✅ dynamic_seed_max 컬럼 추가 완료")
        else:
            print("   ❌ 컬럼 추가 실패")
            return False

        # 5. 데이터 확인
        cursor.execute("SELECT name, seed, dynamic_seed_max FROM bot_info")
        rows = cursor.fetchall()
        print(f"\n📊 현재 BotInfo 데이터 ({len(rows)}개):")
        for name, seed, dynamic_seed_max in rows:
            print(f"   - {name}: seed={seed}, dynamic_seed_max={dynamic_seed_max}")

        print("\n" + "=" * 80)
        print("✅ 마이그레이션 완료!")
        print("=" * 80)
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 마이그레이션 실패: {str(e)}")
        print(f"💡 백업 파일로 복구하세요: {backup_path}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_bot_info()
