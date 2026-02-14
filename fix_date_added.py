"""
DB 수정 스크립트: 잘못된 date_added 수정

어제(2026-02-13) Trade/History 복구 시 잘못된 date_added로 인한 Primary Key 오류 수정
"""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "data" / "persistence" / "sqlalchemy" / "db"

# 수정할 데이터 정의
FIXES = {
    'egg_chan.db': {
        'history': [
            {
                'name': 'TQ_1',
                'wrong_date': '2026-02-13',
                'correct_date': '2025-10-30 04:40:15.937113',
                'description': 'TQ_1 history date_added 수정'
            },
            {
                'name': 'TQ_2',
                'wrong_date': '2026-02-13',
                'correct_date': '2025-12-17 05:30:31.773524',
                'description': 'TQ_2 history date_added 수정'
            }
        ],
        'trade': []
    },
    'egg_choe.db': {
        'history': [
            {
                'name': 'SO_1',
                'wrong_date': '2026-02-13',
                'correct_date': '2025-12-09 09:51:50.009483',
                'description': 'SO_1 history date_added 수정'
            },
            {
                'name': 'SO_2',
                'wrong_date': '2026-02-13',
                'correct_date': '2026-01-01 05:30:22.861719',
                'description': 'SO_2 history date_added 수정'
            }
        ],
        'trade': [
            {
                'name': 'SO_1',
                'symbol': 'SOXL',
                'wrong_date': '2026-02-13 05:30:01',
                'correct_date': '2025-12-09 09:51:50.009483',
                'description': 'SO_1 trade date_added 수정 (PRIMARY KEY)'
            }
        ]
    }
}


def fix_history(conn, cursor, fix_info):
    """History 테이블 date_added 수정"""
    name = fix_info['name']
    wrong_date = fix_info['wrong_date']
    correct_date = fix_info['correct_date']

    # 수정 대상 확인
    cursor.execute(
        "SELECT COUNT(*) FROM history WHERE name = ? AND date_added >= ?",
        (name, wrong_date)
    )
    count = cursor.fetchone()[0]

    if count == 0:
        print(f"  ⚠️  {name}: 수정할 레코드 없음")
        return False

    print(f"  🔄 {name}: {count}개 레코드 수정 중...")
    print(f"     {wrong_date} → {correct_date}")

    # UPDATE 실행
    cursor.execute(
        """UPDATE history
           SET date_added = ?
           WHERE name = ? AND date_added >= ?""",
        (correct_date, name, wrong_date)
    )

    print(f"  ✅ {name}: {cursor.rowcount}개 레코드 수정 완료")
    return True


def fix_trade(conn, cursor, fix_info):
    """Trade 테이블 date_added 수정 (PRIMARY KEY 포함)"""
    name = fix_info['name']
    symbol = fix_info['symbol']
    wrong_date = fix_info['wrong_date']
    correct_date = fix_info['correct_date']

    # 기존 레코드 조회
    cursor.execute(
        "SELECT * FROM trade WHERE name = ? AND date_added = ?",
        (name, wrong_date)
    )
    row = cursor.fetchone()

    if not row:
        print(f"  ⚠️  {name}: 수정할 레코드 없음")
        return False

    print(f"  🔄 {name}: Trade 레코드 수정 중...")
    print(f"     PRIMARY KEY date_added: {wrong_date} → {correct_date}")

    # 컬럼명 조회
    cursor.execute("PRAGMA table_info(trade)")
    columns = [col[1] for col in cursor.fetchall()]

    # 기존 데이터를 dict로 변환
    data = dict(zip(columns, row))

    # 1. 기존 레코드 삭제 (PRIMARY KEY가 변경되므로)
    cursor.execute(
        "DELETE FROM trade WHERE name = ? AND date_added = ?",
        (name, wrong_date)
    )
    print(f"     ✓ 기존 레코드 삭제")

    # 2. 새 date_added로 INSERT
    data['date_added'] = correct_date

    placeholders = ', '.join(['?' for _ in columns])
    cursor.execute(
        f"INSERT INTO trade ({', '.join(columns)}) VALUES ({placeholders})",
        [data[col] for col in columns]
    )
    print(f"     ✓ 새 레코드 삽입 (date_added={correct_date})")
    print(f"  ✅ {name}: Trade 수정 완료")
    return True


def fix_database(db_name, fixes):
    """단일 DB 수정"""
    db_path = DB_DIR / db_name

    print(f"\n{'='*60}")
    print(f"📂 {db_name} 수정 시작")
    print(f"{'='*60}")

    if not db_path.exists():
        print(f"❌ DB 파일이 존재하지 않습니다: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # History 수정
        if fixes['history']:
            print(f"\n[History 테이블 수정]")
            for fix_info in fixes['history']:
                fix_history(conn, cursor, fix_info)

        # Trade 수정
        if fixes['trade']:
            print(f"\n[Trade 테이블 수정]")
            for fix_info in fixes['trade']:
                fix_trade(conn, cursor, fix_info)

        # 커밋
        conn.commit()
        print(f"\n✅ {db_name} 수정 완료!")
        return True

    except Exception as e:
        print(f"\n❌ {db_name} 수정 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_fixes():
    """수정 결과 검증"""
    print(f"\n{'='*60}")
    print(f"🔍 수정 결과 검증")
    print(f"{'='*60}")

    for db_name in FIXES.keys():
        db_path = DB_DIR / db_name
        if not db_path.exists():
            continue

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print(f"\n📂 {db_name}")

        # 2026-02-13 date_added가 남아있는지 확인
        cursor.execute(
            "SELECT name, COUNT(*) FROM history WHERE date_added >= '2026-02-13' GROUP BY name"
        )
        history_results = cursor.fetchall()

        if history_results:
            print(f"  ⚠️  History에 2026-02-13 이후 date_added 남아있음:")
            for name, count in history_results:
                print(f"     - {name}: {count}개")
        else:
            print(f"  ✅ History 수정 완료 (2026-02-13 date_added 없음)")

        cursor.execute(
            "SELECT name, COUNT(*) FROM trade WHERE date_added >= '2026-02-13' GROUP BY name"
        )
        trade_results = cursor.fetchall()

        if trade_results:
            print(f"  ⚠️  Trade에 2026-02-13 이후 date_added 남아있음:")
            for name, count in trade_results:
                print(f"     - {name}: {count}개")
        else:
            print(f"  ✅ Trade 수정 완료 (2026-02-13 date_added 없음)")

        conn.close()


def main():
    print("="*60)
    print("🔧 EggMoney DB 수정 스크립트")
    print("   - 잘못된 date_added 수정 (2026-02-13 → 올바른 날짜)")
    print("="*60)

    results = {}
    for db_name, fixes in FIXES.items():
        results[db_name] = fix_database(db_name, fixes)

    # 검증
    verify_fixes()

    # 결과 요약
    print(f"\n{'='*60}")
    print(f"📋 최종 결과")
    print(f"{'='*60}")
    for db_name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {db_name}: {status}")
    print("="*60)


if __name__ == '__main__':
    main()
