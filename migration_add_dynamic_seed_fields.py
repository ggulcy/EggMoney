"""
마이그레이션: 동적 시드 관련 필드 추가

추가 필드:
- dynamic_seed_enabled: 동적 시드 활성화 여부 (기본값: False)
- dynamic_seed_multiplier: 증액 배수 (기본값: 1.3)
- dynamic_seed_t_threshold: T값 임계점 (기본값: 0.3)
- dynamic_seed_drop_rate: 하락률 기준 (기본값: 0.03)
"""
import sqlite3
import os

# ===== 계정 설정 (수정 필요) =====
ACCOUNT = "sk"  # 계정 이름: chan, choe, sk 등
# ================================

# DB 경로 설정
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'persistence', 'sqlalchemy', 'db', f'egg_{ACCOUNT}.db')


def migrate():
    """마이그레이션 실행"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 기존 컬럼 확인
    cursor.execute("PRAGMA table_info(bot_info)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    migrations = [
        ("dynamic_seed_enabled", "BOOLEAN", "0"),
        ("dynamic_seed_multiplier", "REAL", "0.3"),
        ("dynamic_seed_t_threshold", "REAL", "1.0"),
        ("dynamic_seed_drop_rate", "REAL", "0.03"),
    ]

    for column_name, column_type, default_value in migrations:
        if column_name not in existing_columns:
            sql = f"ALTER TABLE bot_info ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            print(f"✅ 컬럼 추가: {column_name} ({column_type}, default={default_value})")
            cursor.execute(sql)
        else:
            print(f"⏭️ 컬럼 이미 존재: {column_name}")

    conn.commit()
    conn.close()
    print("\n🎉 마이그레이션 완료!")


if __name__ == '__main__':
    migrate()
