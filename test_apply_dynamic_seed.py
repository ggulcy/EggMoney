"""
apply_dynamic_seed 목데이터 테스트

새 로직 검증:
1. 같은 심볼은 시드 작은 봇만 증액
2. T값 1/3 돌파 시 강제 증액
3. 전일대비 하락 시 증액
"""
from dataclasses import dataclass
from typing import Optional, List, Set


@dataclass
class MockBotInfo:
    """테스트용 봇 정보"""
    name: str
    symbol: str
    seed: float
    max_tier: int
    dynamic_seed_max: float
    total_investment: float  # T값 계산용
    dynamic_seed_enabled: bool = True
    dynamic_seed_multiplier: float = 0.3  # 30% 증액
    dynamic_seed_t_threshold: float = 0.3
    dynamic_seed_drop_rate: float = 0.03


@dataclass
class MockPriceData:
    """테스트용 가격 데이터"""
    prev_close: float
    current_price: float


def get_T(total: float, seed: float) -> float:
    """T값 계산"""
    return round(total / seed, 2)


def simulate_process_dynamic_seed(
        bot: MockBotInfo,
        price_data: MockPriceData
) -> dict:
    """개별 봇 동적 시드 처리 시뮬레이션"""
    old_seed = bot.seed

    # 하락률 계산
    drop_rate = None
    if price_data.prev_close > 0:
        drop_rate = (price_data.prev_close - price_data.current_price) / price_data.prev_close

    # T값 계산
    t = get_T(bot.total_investment, bot.seed)
    t_threshold = bot.max_tier * bot.dynamic_seed_t_threshold

    # 트리거 판별
    t_triggered = t >= t_threshold
    drop_triggered = drop_rate is not None and drop_rate >= bot.dynamic_seed_drop_rate

    result = {
        'bot_name': bot.name,
        'symbol': bot.symbol,
        'old_seed': old_seed,
        'new_seed': old_seed,
        't_value': t,
        't_threshold': t_threshold,
        'drop_rate': drop_rate,
        'drop_interval': bot.dynamic_seed_drop_rate,
        't_triggered': t_triggered,
        'drop_triggered': drop_triggered,
        'applied': False,
        'trigger': None
    }

    if t_triggered or drop_triggered:
        target_seed = min(old_seed * (1 + bot.dynamic_seed_multiplier), bot.dynamic_seed_max)
        if target_seed > old_seed:
            result['new_seed'] = target_seed
            result['applied'] = True
            if t_triggered:
                result['trigger'] = f"T값 {t:.1f} (기준: {t_threshold:.1f} 돌파)"
            else:
                result['trigger'] = f"전일대비 {drop_rate * 100:.1f}% 하락"

    return result


def simulate_apply_dynamic_seed(bots: List[MockBotInfo], price_data_map: dict) -> List[dict]:
    """apply_dynamic_seed 전체 시뮬레이션"""
    # 시드 오름차순 정렬
    sorted_bots = sorted(bots, key=lambda x: x.seed)

    processed_symbols: Set[str] = set()
    results = []

    for bot in sorted_bots:
        # 스킵 조건
        if not bot.dynamic_seed_enabled:
            results.append({'bot_name': bot.name, 'skipped': 'dynamic_seed_enabled is False'})
            continue
        if bot.seed >= bot.dynamic_seed_max:
            results.append({'bot_name': bot.name, 'skipped': 'already at max'})
            continue
        if bot.symbol in processed_symbols:
            results.append({'bot_name': bot.name, 'skipped': f'symbol {bot.symbol} already processed'})
            continue

        price_data = price_data_map.get(bot.symbol)
        if not price_data:
            results.append({'bot_name': bot.name, 'skipped': 'no price data'})
            continue

        result = simulate_process_dynamic_seed(bot, price_data)
        results.append(result)

        if result['applied']:
            processed_symbols.add(bot.symbol)

    return results


def run_test():
    """테스트 실행"""

    print("=" * 70)
    print("📊 apply_dynamic_seed 새 로직 테스트")
    print("=" * 70)

    # ===== 테스트 1: 같은 심볼 중복 증액 방지 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 1: 같은 심볼 중복 증액 방지 (시드 작은 봇 우선)")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=1000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),
        MockBotInfo(name="TQ_2", symbol="TQQQ", seed=500.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),  # 시드 작음
        MockBotInfo(name="TQ_3", symbol="TQQQ", seed=2000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=95.0),  # 5% 하락
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    for r in results:
        if 'skipped' in r:
            print(f"  [{r['bot_name']}] ⏭️ 스킵: {r['skipped']}")
        elif r['applied']:
            print(f"  [{r['bot_name']}] ✅ 증액: ${r['old_seed']:.0f} → ${r['new_seed']:.0f} ({r['trigger']})")
        else:
            print(f"  [{r['bot_name']}] ⏸️ 유지: ${r['old_seed']:.0f}")

    # 검증
    applied_count = sum(1 for r in results if r.get('applied'))
    assert applied_count == 1, f"❌ 같은 심볼인데 {applied_count}개 증액됨"
    assert results[0]['applied'] and results[0]['bot_name'] == 'TQ_2', "❌ 시드 작은 TQ_2가 먼저 처리되어야 함"
    print("  ✅ 통과: TQ_2만 증액됨")

    # ===== 테스트 2: T값 기반 강제 증액 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 2: T값 기반 강제 증액 (max_tier=9, T>=3이면 증액)")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=1000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=3500.0),  # T=3.5
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=100.0),  # 하락 없음
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    r = results[0]
    print(f"  T값: {r['t_value']:.1f}, 기준: {r['t_threshold']:.1f}")
    print(f"  하락률: {r['drop_rate']*100:.1f}%, 기준: {r['drop_interval']*100:.0f}%")

    if r['applied']:
        print(f"  ✅ 증액: ${r['old_seed']:.0f} → ${r['new_seed']:.0f} ({r['trigger']})")
    else:
        print(f"  ⏸️ 유지: ${r['old_seed']:.0f}")

    assert r['applied'], "❌ T값 3.5 >= 3 인데 증액 안됨"
    assert r['t_triggered'], "❌ T값 트리거가 아님"
    print("  ✅ 통과: T값으로 증액됨")

    # ===== 테스트 3: 전일대비 하락 기반 증액 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 3: 전일대비 하락 기반 증액 (TQQQ 기준 3%)")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=1000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),  # T=0.1
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=95.0),  # 5% 하락
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    r = results[0]
    print(f"  T값: {r['t_value']:.1f}, 기준: {r['t_threshold']:.1f}")
    print(f"  하락률: {r['drop_rate']*100:.1f}%, 기준: {r['drop_interval']*100:.0f}%")

    if r['applied']:
        print(f"  ✅ 증액: ${r['old_seed']:.0f} → ${r['new_seed']:.0f} ({r['trigger']})")

    assert r['applied'], "❌ 5% 하락인데 증액 안됨"
    assert r['drop_triggered'], "❌ 하락 트리거가 아님"
    print("  ✅ 통과: 하락으로 증액됨")

    # ===== 테스트 4: 기준 미달 시 증액 안됨 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 4: 기준 미달 시 증액 안됨")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=1000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=1000.0),  # T=1
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=99.0),  # 1% 하락
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    r = results[0]
    print(f"  T값: {r['t_value']:.1f}, 기준: {r['t_threshold']:.1f}")
    print(f"  하락률: {r['drop_rate']*100:.1f}%, 기준: {r['drop_interval']*100:.0f}%")
    print(f"  ⏸️ 유지: ${r['old_seed']:.0f}")

    assert not r['applied'], "❌ 기준 미달인데 증액됨"
    print("  ✅ 통과: 기준 미달로 유지")

    # ===== 테스트 5: dynamic_seed_max 제한 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 5: dynamic_seed_max 제한")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=900.0, max_tier=9, dynamic_seed_max=1000.0, total_investment=100.0),
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=95.0),  # 5% 하락
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    r = results[0]
    print(f"  원래 시드: ${r['old_seed']:.0f}")
    print(f"  1.3배: ${r['old_seed'] * 1.3:.0f}")
    print(f"  max: $1000")

    if r['applied']:
        print(f"  ✅ 증액: ${r['old_seed']:.0f} → ${r['new_seed']:.0f}")

    assert r['new_seed'] == 1000.0, f"❌ max 제한 안됨: {r['new_seed']}"
    print("  ✅ 통과: max로 제한됨")

    # ===== 테스트 6: 다른 심볼은 각각 증액 =====
    print(f"\n{'─' * 70}")
    print("📌 테스트 6: 다른 심볼은 각각 증액")
    print(f"{'─' * 70}")

    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=1000.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),
        MockBotInfo(name="SX_1", symbol="SOXL", seed=500.0, max_tier=9, dynamic_seed_max=10000.0, total_investment=100.0),
    ]

    price_data = {
        "TQQQ": MockPriceData(prev_close=100.0, current_price=95.0),
        "SOXL": MockPriceData(prev_close=100.0, current_price=95.0),
    }

    results = simulate_apply_dynamic_seed(bots, price_data)
    for r in results:
        if r['applied']:
            print(f"  [{r['bot_name']}] ✅ 증액: ${r['old_seed']:.0f} → ${r['new_seed']:.0f}")

    applied_count = sum(1 for r in results if r.get('applied'))
    assert applied_count == 2, f"❌ 다른 심볼인데 {applied_count}개만 증액됨"
    print("  ✅ 통과: 둘 다 증액됨")

    print(f"\n{'=' * 70}")
    print("🎉 모든 테스트 통과!")
    print("=" * 70)


if __name__ == '__main__':
    run_test()
