# -*- coding: utf-8 -*-
"""Market Data 캐싱 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from data.external.market_data.market_data_client import MarketDataClient, CacheInfo
from data.external.market_data.market_data_service import MarketDataService
from config import key_store


def test_vix_caching():
    """VIX 캐싱 테스트: 첫 호출은 API, 두 번째는 캐시"""
    print("\n" + "=" * 60)
    print("🧪 VIX 캐싱 테스트")
    print("=" * 60)

    client = MarketDataClient()

    # 캐시 초기화 (테스트 위해) - 히스토리 기반으로 변경됨
    key_store.delete("^VIX_YF_DATA_TIMESTAMP")
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "market_cache", "^VIX.csv"
    )
    if os.path.exists(csv_path):
        os.remove(csv_path)
        print(f"🗑️ 기존 VIX 캐시 파일 삭제: {csv_path}")

    # 첫 번째 호출: API에서 가져와야 함
    print("\n[1차 호출] API에서 데이터 조회 예상...")
    result1 = client.fetch_vix_data(cache_hours=6)

    if result1 is None:
        print("❌ VIX 데이터 조회 실패")
        return False

    print(f"  - VIX 값: {result1.value}")
    print(f"  - 캐시에서 가져옴: {result1.cache_info.is_from_cache}")
    print(f"  - 캐시 시간: {result1.cache_info.cached_at}")

    if result1.cache_info.is_from_cache:
        print("❌ 실패: 첫 호출인데 캐시에서 가져옴")
        return False

    print("✅ 첫 호출: API에서 정상 조회")

    # 두 번째 호출: 캐시에서 가져와야 함
    print("\n[2차 호출] 캐시에서 데이터 조회 예상...")
    result2 = client.fetch_vix_data(cache_hours=6)

    if result2 is None:
        print("❌ VIX 데이터 조회 실패")
        return False

    print(f"  - VIX 값: {result2.value}")
    print(f"  - 캐시에서 가져옴: {result2.cache_info.is_from_cache}")
    print(f"  - 경과 시간: {result2.cache_info.elapsed_hours}시간")

    if not result2.cache_info.is_from_cache:
        print("❌ 실패: 두 번째 호출인데 API에서 가져옴")
        return False

    print("✅ 두 번째 호출: 캐시에서 정상 조회")

    # 값이 동일한지 확인
    if result1.value == result2.value:
        print(f"✅ 값 일치: {result1.value} == {result2.value}")
    else:
        print(f"⚠️ 값 불일치: {result1.value} != {result2.value}")

    return True


def test_ticker_caching():
    """티커 히스토리 캐싱 테스트"""
    print("\n" + "=" * 60)
    print("🧪 티커 히스토리 캐싱 테스트 (TQQQ)")
    print("=" * 60)

    client = MarketDataClient()
    ticker = "TQQQ"

    # 캐시 초기화
    key_store.delete(f"{ticker}_YF_DATA_TIMESTAMP")
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "market_cache", f"{ticker}.csv"
    )
    if os.path.exists(csv_path):
        os.remove(csv_path)
        print(f"🗑️ 기존 캐시 파일 삭제: {csv_path}")

    # 첫 번째 호출
    print("\n[1차 호출] API에서 데이터 조회 예상...")
    result1 = client.fetch_ticker_history(ticker, cache_hours=6)

    if result1 is None:
        print("❌ 티커 데이터 조회 실패")
        return False

    print(f"  - 데이터 행 수: {len(result1.df)}")
    print(f"  - 캐시에서 가져옴: {result1.cache_info.is_from_cache}")

    if result1.cache_info.is_from_cache:
        print("❌ 실패: 첫 호출인데 캐시에서 가져옴")
        return False

    print("✅ 첫 호출: API에서 정상 조회")

    # 두 번째 호출
    print("\n[2차 호출] 캐시에서 데이터 조회 예상...")
    result2 = client.fetch_ticker_history(ticker, cache_hours=6)

    if result2 is None:
        print("❌ 티커 데이터 조회 실패")
        return False

    print(f"  - 데이터 행 수: {len(result2.df)}")
    print(f"  - 캐시에서 가져옴: {result2.cache_info.is_from_cache}")
    print(f"  - 경과 시간: {result2.cache_info.elapsed_hours}시간")

    if not result2.cache_info.is_from_cache:
        print("❌ 실패: 두 번째 호출인데 API에서 가져옴")
        return False

    print("✅ 두 번째 호출: 캐시에서 정상 조회")

    return True


def test_service_uses_client_cache():
    """Service가 Client의 캐시를 사용하는지 테스트"""
    print("\n" + "=" * 60)
    print("🧪 Service → Client 캐시 연동 테스트")
    print("=" * 60)

    service = MarketDataService()

    # VIX 테스트
    print("\n[VIX Indicator 조회]")
    vix = service.get_vix_indicator(cache_hours=6)
    if vix:
        print(f"  - VIX: {vix.value} ({vix.level})")
        print(f"  - 캐시 시간: {vix.cached_at}")
        print(f"  - 경과: {vix.elapsed_hours}시간")
        print("✅ VIX Indicator 정상")
    else:
        print("❌ VIX Indicator 실패")
        return False

    # RSI 테스트
    print("\n[RSI Indicator 조회 - TQQQ]")
    rsi = service.get_rsi_indicator("TQQQ", cache_hours=6)
    if rsi:
        print(f"  - RSI: {rsi.value} ({rsi.level})")
        print(f"  - 캐시 시간: {rsi.cached_at}")
        print(f"  - 경과: {rsi.elapsed_hours}시간")
        print("✅ RSI Indicator 정상")
    else:
        print("❌ RSI Indicator 실패")
        return False

    return True


def test_cache_expiry():
    """캐시 만료 테스트 (cache_hours=0으로 즉시 만료)"""
    print("\n" + "=" * 60)
    print("🧪 캐시 만료 테스트")
    print("=" * 60)

    client = MarketDataClient()

    # 먼저 캐시 생성
    print("\n[캐시 생성]")
    result1 = client.fetch_vix_data(cache_hours=6)
    if result1:
        print(f"  - VIX: {result1.value}, 캐시: {result1.cache_info.is_from_cache}")

    # cache_hours=0으로 호출 → 캐시 만료로 처리되어야 함
    print("\n[cache_hours=0으로 호출 - 캐시 만료 예상]")
    result2 = client.fetch_vix_data(cache_hours=0)
    if result2:
        print(f"  - VIX: {result2.value}, 캐시: {result2.cache_info.is_from_cache}")
        if not result2.cache_info.is_from_cache:
            print("✅ cache_hours=0일 때 API에서 새로 조회")
            return True
        else:
            print("❌ 실패: cache_hours=0인데 캐시에서 가져옴")
            return False

    return False


def test_vix_history():
    """VIX 히스토리 저장 테스트"""
    print("\n" + "=" * 60)
    print("🧪 VIX 히스토리 저장 테스트")
    print("=" * 60)

    client = MarketDataClient()

    # VIX 히스토리 조회
    print("\n[VIX 히스토리 조회]")
    result = client.fetch_vix_history(cache_hours=6)

    if result is None:
        print("❌ VIX 히스토리 조회 실패")
        return False

    print(f"  - 데이터 행 수: {len(result.df)}")
    print(f"  - 기간: {result.df.index[0].date()} ~ {result.df.index[-1].date()}")
    print(f"  - 컬럼: {list(result.df.columns)}")
    print(f"  - 최신 Close: {result.df['Close'].iloc[-1]:.2f}")
    print(f"  - 캐시에서 가져옴: {result.cache_info.is_from_cache}")

    # CSV 파일 확인
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "market_cache", "^VIX.csv"
    )
    if os.path.exists(csv_path):
        print(f"✅ CSV 파일 생성됨: {csv_path}")
    else:
        print("❌ CSV 파일이 생성되지 않음")
        return False

    # 30일치 데이터 있는지 확인
    if len(result.df) >= 30:
        print(f"✅ 30일 이상 데이터 보유 ({len(result.df)}일)")
    else:
        print(f"⚠️ 데이터가 30일 미만 ({len(result.df)}일)")

    return True


if __name__ == "__main__":
    print("🚀 Market Data 캐싱 테스트 시작")
    print(f"📅 테스트 시간: {datetime.now().isoformat()}")

    results = []

    results.append(("VIX 캐싱", test_vix_caching()))
    results.append(("VIX 히스토리", test_vix_history()))
    results.append(("티커 캐싱", test_ticker_caching()))
    results.append(("Service 연동", test_service_uses_client_cache()))
    results.append(("캐시 만료", test_cache_expiry()))

    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + ("🎉 모든 테스트 통과!" if all_passed else "⚠️ 일부 테스트 실패"))
