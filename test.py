from config.dependencies import init_dependencies, get_dependencies
from usecase.market_usecase import MarketUsecase
from config.util import get_seed_ratio_by_drawdown


def test_drawdown():
    """MarketUsecase drawdown 테스트"""
    init_dependencies(test_mode=True)
    deps = get_dependencies()
    market_usecase = MarketUsecase(
        market_indicator_repo=deps.market_indicator_repo,
        exchange_repo=deps.exchange_repo
    )

    tickers = ["QQQ", "TQQQ", "SOXL"]
    for ticker in tickers:
        result = market_usecase.get_drawdown(ticker=ticker, days=90)
        if result:
            print(f"\n[{result['ticker']}] Drawdown 결과:")
            print(f"  기간: {result['period_days']}일")
            print(f"  고점: ${result['high_price']:.2f} ({result['high_date']})")
            print(f"  현재: ${result['current_price']:.2f} ({result['current_date']})")
            print(f"  하락률: {result['drawdown_rate'] * 100:.2f}%")
        else:
            print(f"\n[{ticker}] 조회 실패")



def test_seed_ratio():
    """Drawdown 기반 시드 비율 계산 테스트"""
    init_dependencies(test_mode=True)
    deps = get_dependencies()
    market_usecase = MarketUsecase(
        market_indicator_repo=deps.market_indicator_repo,
        exchange_repo=deps.exchange_repo
    )

    # 티커별 설정: (ticker, interval_rate, max_count)
    configs = [
        ("TQQQ", 0.03, 10),  # TQQQ: 인터벌 3%, 최대 10회
        ("SOXL", 0.05, 10),  # SOXL: 인터벌 5%, 최대 10회
    ]

    print("=" * 60)
    print("📊 Drawdown 기반 시드 비율 계산")
    print("=" * 60)

    for ticker, interval_rate, max_count in configs:
        result = market_usecase.get_drawdown(ticker=ticker, days=90)

        if result:
            drawdown_rate = result['drawdown_rate']
            seed_ratio = get_seed_ratio_by_drawdown(
                drawdown_rate=drawdown_rate,
                interval_rate=interval_rate,
                max_count=max_count
            )
            drop_count = int(abs(drawdown_rate) / interval_rate)
            drop_count = min(drop_count, max_count)

            print(f"\n[{ticker}]")
            print(f"  고점: ${result['high_price']:.2f} → 현재: ${result['current_price']:.2f}")
            print(f"  하락률: {drawdown_rate * 100:.2f}%")
            print(f"  설정: 인터벌 {interval_rate * 100:.0f}%, 최대 {max_count}회")
            print(f"  하락 카운트: {drop_count}/{max_count}")
            print(f"  ✅ 시드 비율: {seed_ratio * 100:.0f}% (max 시드 대비)")
        else:
            print(f"\n[{ticker}] 조회 실패")


if __name__ == '__main__':
    test_seed_ratio()
