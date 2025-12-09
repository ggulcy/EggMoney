"""
History 테이블 스키마 마이그레이션 스크립트

변경 사항:
- sell_date 컬럼 → trade_date 컬럼으로 이름 변경
- amount 컬럼 추가 (기존 데이터는 profit / (sell_price - buy_price)로 계산)

사용법:
    python migrate_history_schema.py [admin]

예시:
    python migrate_history_schema.py chan
    python migrate_history_schema.py choe
    python migrate_history_schema.py sk
"""
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime


def migrate_history():
    """History 테이블 마이그레이션 실행"""

    admin = "sk"
    # DB 경로 설정
    db_path = Path(__file__).parent / "data" / "persistence" / "sqlalchemy" / "db" / f"egg_{admin}.db"

    print("=" * 80)
    print(f"🔄 History 테이블 스키마 마이그레이션 시작 (admin: {admin})")
    print("=" * 80)

    if not db_path.exists():
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return False

    print(f"📍 대상 DB: {db_path}")

    # 백업 생성
    backup_path = db_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"📦 백업 생성: {backup_path.name}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 기존 데이터 조회
        print("\n📥 기존 History 데이터 조회 중...")
        cursor.execute("""
            SELECT date_added, sell_date, trade_type, name, symbol,
                   buy_price, sell_price, profit, profit_rate
            FROM history
        """)
        old_data = cursor.fetchall()
        print(f"   - {len(old_data)}개 레코드 발견")

        # 2. 기존 테이블 삭제
        print("\n🗑️  기존 history 테이블 삭제...")
        cursor.execute("DROP TABLE IF EXISTS history")

        # 3. 새로운 테이블 생성 (trade_date, amount 추가)
        print("📝 새로운 history 테이블 생성...")
        cursor.execute("""
            CREATE TABLE history (
                date_added DATETIME NOT NULL,
                trade_date DATETIME NOT NULL,
                trade_type VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                buy_price FLOAT NOT NULL,
                sell_price FLOAT NOT NULL,
                amount FLOAT NOT NULL,
                profit FLOAT NOT NULL,
                profit_rate FLOAT NOT NULL,
                PRIMARY KEY (date_added, trade_date, trade_type, name)
            )
        """)

        # 4. 데이터 마이그레이션 (amount 계산 포함)
        print("📥 데이터 마이그레이션 중...")
        migrated_count = 0
        skipped_count = 0

        for row in old_data:
            date_added, sell_date, trade_type, name, symbol, buy_price, sell_price, profit, profit_rate = row

            # amount 계산: profit / (sell_price - buy_price)
            price_diff = sell_price - buy_price
            if price_diff != 0:
                amount = round(profit / price_diff)
            else:
                amount = 0
                skipped_count += 1

            cursor.execute("""
                INSERT INTO history
                (date_added, trade_date, trade_type, name, symbol,
                 buy_price, sell_price, amount, profit, profit_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_added, sell_date, trade_type, name, symbol,
                  buy_price, sell_price, amount, profit, profit_rate))
            migrated_count += 1

        conn.commit()

        print(f"   ✅ {migrated_count}개 레코드 마이그레이션 완료")
        if skipped_count > 0:
            print(f"   ⚠️  {skipped_count}개 레코드의 amount가 0으로 설정됨 (price_diff=0)")

        # 5. 검증
        print("\n🔍 마이그레이션 검증...")
        cursor.execute("SELECT COUNT(*) FROM history")
        new_count = cursor.fetchone()[0]

        cursor.execute("PRAGMA table_info(history)")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"   - 레코드 수: {new_count}")
        print(f"   - 컬럼 목록: {columns}")

        if 'trade_date' in columns and 'amount' in columns and 'sell_date' not in columns:
            print("   ✅ 스키마 변경 확인 완료")
        else:
            print("   ❌ 스키마 변경 실패")
            return False

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
    migrate_history()
