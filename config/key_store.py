"""설정값 저장/조회를 위한 Key-Value Store (JSON 기반)"""
import os
import json
from threading import Lock

# === 프로젝트 루트 기준 경로 설정 ===
# __file__: .../config/key_store.py
# 프로젝트 루트: .../EggMoney
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR = os.path.join(PROJECT_ROOT, "data", "persistence", "sqlalchemy", "db")
os.makedirs(BASE_DIR, exist_ok=True)
KEY_STORE_PATH = os.path.join(BASE_DIR, "key_store.json")


# 파일 락 (동시 접근 방지)
_lock = Lock()

# === Key 상수 정의 ===
AT_KEY = "AT_KEY"
AT_EX_DATE = "AT_EX_DATE"

TRADE_TIME = "TRADE_TIME"
TWAP_TIME = "TWAP_TIME"
TWAP_COUNT = "TWAP_COUNT"
CLOSING_BUY_TIME = "CLOSING_BUY_TIME"

IS_DYNAMIC_SEED_APPLY_TODAY = "IS_DYNAMIC_SEED_APPLY_TODAY"

TOTAL_BUDGET = "TOTAL_BUDGET"  # 사용자 지정 총 예산
AUTO_START = "AUTO_START"  # 다음 봇 자동 출발 여부
AUTO_START_THRESHOLD = "AUTO_START_THRESHOLD"  # 자동 출발 T값 임계 비율 (예: 0.3 = max_tier의 30%)


def _get_default_values():
    """기본값 딕셔너리 반환"""
    # 서머타임을 고려한 TWAP_TIME 기본값 가져오기
    from config.util import get_twap_times, get_closing_buy_times

    return {
        TRADE_TIME: "00:05",
        TWAP_TIME: get_twap_times(),
        TWAP_COUNT: 5,
        CLOSING_BUY_TIME: get_closing_buy_times(),
        AUTO_START: False,  # 기본값: 자동 출발 비활성화
        AUTO_START_THRESHOLD: 0.5  # 기본값: max_tier의 50%
    }


def _load_db():
    """JSON 파일에서 데이터 로드"""
    if not os.path.exists(KEY_STORE_PATH):
        print(f"[key_store] File not found, creating with default values: {KEY_STORE_PATH}")
        # 기본값으로 JSON 파일 생성
        default_data = _get_default_values()
        _save_db(default_data)
        return default_data

    try:
        with open(KEY_STORE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 기존 파일이 있더라도 없는 키는 기본값으로 추가
        default_data = _get_default_values()
        updated = False
        for key, value in default_data.items():
            if key not in data:
                print(f"[key_store] Adding missing key '{key}' with default value: {value}")
                data[key] = value
                updated = True

        # 추가된 키가 있으면 파일 저장
        if updated:
            _save_db(data)

        return data
    except Exception as e:
        print(f"[key_store] Warning: Failed to load {KEY_STORE_PATH}: {e}")
        return {}


def _save_db(data):
    """JSON 파일에 데이터 저장"""
    try:
        with open(KEY_STORE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[key_store] Error: Failed to save {KEY_STORE_PATH}: {e}")


def write(key, value):
    """키와 값을 JSON 파일에 저장합니다."""
    print(f"[key_store] write({key}, {value}) to {KEY_STORE_PATH}")
    with _lock:
        db = _load_db()
        db[key] = value
        _save_db(db)
        print(f"[key_store] write successful, file exists: {os.path.exists(KEY_STORE_PATH)}")


def read(key):
    """주어진 키에 해당하는 값을 JSON 파일에서 읽어 반환합니다."""
    with _lock:
        db = _load_db()
        if key == "TRADE_TIME":
            trade_time = db.get(key)
            return trade_time if trade_time else "00:05"
        elif key == "TWAP_TIME":
            twap_time = db.get(key)
            if twap_time:
                return twap_time
            # 서머타임을 고려한 기본값 반환 (circular import 방지를 위해 함수 내부에서 import)
            from config.util import get_twap_times
            return get_twap_times()
        elif key == "TWAP_COUNT":
            twap_count = db.get(key)
            return twap_count if twap_count else 5
        elif key == "IS_DYNAMIC_SEED_APPLY_TODAY":
            is_apply = db.get(key)
            return is_apply if is_apply else False
        elif key == "TOTAL_BUDGET":
            total_budget = db.get(key)
            return total_budget if total_budget is not None else None
        elif key == "AUTO_START":
            auto_start = db.get(key)
            return auto_start if auto_start is not None else False
        elif key == "AUTO_START_THRESHOLD":
            threshold = db.get(key)
            return threshold if threshold is not None else 0.5
        elif key == "CLOSING_BUY_TIME":
            closing_buy_time = db.get(key)
            if closing_buy_time:
                return closing_buy_time
            from config.util import get_closing_buy_times
            return get_closing_buy_times()
        return db.get(key, None)


def print_all_keys():
    """현재 key_store에 저장된 모든 키와 값을 출력합니다."""
    with _lock:
        db = _load_db()
        if not db:
            print("📂 key_store에 저장된 데이터가 없습니다.")
            return

        print(f"📋 총 {len(db)}개의 항목이 있습니다:")
        for key, value in db.items():
            print(f"🔑 {key} → {value}")


def get_all_keys():
    """JSON 파일에 저장된 모든 키를 반환합니다."""
    with _lock:
        db = _load_db()
        return list(db.keys())


def delete(key):
    """주어진 키를 JSON 파일에서 삭제합니다."""
    with _lock:
        db = _load_db()
        if key in db:
            del db[key]
            _save_db(db)



