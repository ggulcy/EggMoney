"""
apply_dynamic_seed 목데이터 테스트

시나리오별 시드 변화 시뮬레이션
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from config.item import get_drop_interval_rate
from config.util import get_seed_ratio_by_drawdown


@dataclass
class MockBotInfo:
    """테스트용 봇 정보"""
    name: str
    symbol: str
    seed: float
    dynamic_seed_max: float


@dataclass
class MockPriceData:
    """테스트용 가격 데이터"""
    prev_close: float
    current_price: float
    high_price_90d: float


def simulate_daily_drop_seed(
        current_seed: float,
        drop_interval_rate: float,
        prev_close: float,
        current_price: float
) -> Optional[Dict[str, Any]]:
    """1단계: 전일대비 하락 시뮬레이션"""
    MULTIPLIER = 1.5

    if prev_close <= 0:
        return None

    drop_rate = (prev_close - current_price) / prev_close

    if drop_rate < drop_interval_rate:
        return None

    return {
        'target_seed': current_seed * MULTIPLIER,
        'trigger': f"전일대비 {drop_rate * 100:.1f}% 하락"
    }


def simulate_drawdown_seed(
        dynamic_seed_max: float,
        drop_interval_rate: float,
        high_price: float,
        current_price: float
) -> Optional[Dict[str, Any]]:
    """2단계: 고점대비 하락률 시뮬레이션"""
    MAX_COUNT = 10

    if high_price <= 0:
        return None

    drawdown_rate = (current_price - high_price) / high_price

    seed_ratio = get_seed_ratio_by_drawdown(
        drawdown_rate=drawdown_rate,
        interval_rate=drop_interval_rate,
        max_count=MAX_COUNT
    )

    target_seed = dynamic_seed_max * seed_ratio

    if target_seed <= 0:
        return None

    return {
        'target_seed': target_seed,
        'trigger': f"고점대비 {drawdown_rate * 100:.1f}% 하락 (ratio: {seed_ratio * 100:.0f}%)"
    }


def simulate_apply_dynamic_seed(
        bot: MockBotInfo,
        price_data: MockPriceData
) -> Dict[str, Any]:
    """apply_dynamic_seed 시뮬레이션"""

    drop_interval_rate = get_drop_interval_rate(bot.symbol)

    old_seed = bot.seed
    target_seed = old_seed
    trigger_reason = None

    # 1단계: 전일대비 하락
    step1_result = simulate_daily_drop_seed(
        current_seed=old_seed,
        drop_interval_rate=drop_interval_rate,
        prev_close=price_data.prev_close,
        current_price=price_data.current_price
    )
    if step1_result:
        target_seed = step1_result['target_seed']
        trigger_reason = step1_result['trigger']

    # 2단계: 고점대비 하락률
    step2_result = simulate_drawdown_seed(
        dynamic_seed_max=bot.dynamic_seed_max,
        drop_interval_rate=drop_interval_rate,
        high_price=price_data.high_price_90d,
        current_price=price_data.current_price
    )
    if step2_result and step2_result['target_seed'] > target_seed:
        target_seed = step2_result['target_seed']
        trigger_reason = step2_result['trigger']

    # 최종 적용
    target_seed = min(target_seed, bot.dynamic_seed_max)

    return {
        'bot_name': bot.name,
        'symbol': bot.symbol,
        'old_seed': old_seed,
        'new_seed': target_seed if target_seed > old_seed else old_seed,
        'trigger': trigger_reason,
        'changed': target_seed > old_seed,
        'step1': step1_result,
        'step2': step2_result,
    }


def run_test():
    """테스트 실행"""

    print("=" * 70)
    print("📊 apply_dynamic_seed 목데이터 테스트")
    print("=" * 70)

    # 테스트 봇 설정
    bots = [
        MockBotInfo(name="TQ_1", symbol="TQQQ", seed=100.0, dynamic_seed_max=1000.0),
        MockBotInfo(name="SX_1", symbol="SOXL", seed=100.0, dynamic_seed_max=1000.0),
    ]

    # 시나리오별 가격 데이터
    scenarios = [
        {
            "name": "평온한 시장",
            "TQQQ": MockPriceData(prev_close=50.0, current_price=49.5, high_price_90d=52.0),  # -1% 전일, -4.8% 고점
            "SOXL": MockPriceData(prev_close=30.0, current_price=29.7, high_price_90d=31.0),  # -1% 전일, -4.2% 고점
        },
        {
            "name": "단기 급락 (전일대비 5% 하락)",
            "TQQQ": MockPriceData(prev_close=50.0, current_price=47.5, high_price_90d=52.0),  # -5% 전일, -8.6% 고점
            "SOXL": MockPriceData(prev_close=30.0, current_price=28.5, high_price_90d=31.0),  # -5% 전일, -8.1% 고점
        },
        {
            "name": "장기 하락 (고점대비 15% 하락)",
            "TQQQ": MockPriceData(prev_close=44.2, current_price=44.2, high_price_90d=52.0),  # 0% 전일, -15% 고점
            "SOXL": MockPriceData(prev_close=26.35, current_price=26.35, high_price_90d=31.0),  # 0% 전일, -15% 고점
        },
        {
            "name": "급락 + 장기 하락 (전일 5% + 고점 20%)",
            "TQQQ": MockPriceData(prev_close=43.8, current_price=41.6, high_price_90d=52.0),  # -5% 전일, -20% 고점
            "SOXL": MockPriceData(prev_close=26.1, current_price=24.8, high_price_90d=31.0),  # -5% 전일, -20% 고점
        },
        {
            "name": "대폭락 (고점대비 30% 하락)",
            "TQQQ": MockPriceData(prev_close=36.4, current_price=36.4, high_price_90d=52.0),  # 0% 전일, -30% 고점
            "SOXL": MockPriceData(prev_close=21.7, current_price=21.7, high_price_90d=31.0),  # 0% 전일, -30% 고점
        },
    ]

    for scenario in scenarios:
        print(f"\n{'─' * 70}")
        print(f"📌 시나리오: {scenario['name']}")
        print(f"{'─' * 70}")

        for bot in bots:
            price_data = scenario[bot.symbol]
            result = simulate_apply_dynamic_seed(bot, price_data)

            # 가격 정보
            daily_drop = (price_data.prev_close - price_data.current_price) / price_data.prev_close * 100
            drawdown = (price_data.current_price - price_data.high_price_90d) / price_data.high_price_90d * 100

            print(f"\n[{bot.name}] {bot.symbol}")
            print(f"  가격: 전일 ${price_data.prev_close:.2f} → 현재 ${price_data.current_price:.2f} (전일대비 {daily_drop:+.1f}%)")
            print(f"  고점: ${price_data.high_price_90d:.2f} (고점대비 {drawdown:.1f}%)")
            print(f"  인터벌: {get_drop_interval_rate(bot.symbol) * 100:.0f}%")

            # 단계별 결과
            print(f"  ─────────────────────────────────")
            if result['step1']:
                print(f"  1단계: {result['step1']['trigger']} → 시드 ${result['step1']['target_seed']:.2f}")
            else:
                print(f"  1단계: 조건 미달 (전일대비 하락률 부족)")

            if result['step2']:
                print(f"  2단계: {result['step2']['trigger']} → 시드 ${result['step2']['target_seed']:.2f}")
            else:
                print(f"  2단계: 조건 미달 (고점대비 하락률 부족)")

            # 최종 결과
            print(f"  ─────────────────────────────────")
            if result['changed']:
                print(f"  ✅ 시드 변경: ${result['old_seed']:.2f} → ${result['new_seed']:.2f} (+{(result['new_seed']/result['old_seed']-1)*100:.0f}%)")
                print(f"     트리거: {result['trigger']}")
            else:
                print(f"  ⏸️ 시드 유지: ${result['old_seed']:.2f}")


if __name__ == '__main__':
    run_test()
