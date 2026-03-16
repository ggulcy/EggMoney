import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.dependencies import init_dependencies

deps = init_dependencies(test_mode=True)

all_bots = deps.bot_info_repo.find_all()
if not all_bots:
    print("bot_info가 없습니다")
    sys.exit(1)


bot_info = all_bots[0]
avr = deps.trade_repo.get_average_purchase_price(bot_info.name)

ticker = bot_info.symbol
print(f"bot: {bot_info.name} / ticker: {ticker}")

for days in [5, 10, 20]:
    result = deps.market_indicator_repo.get_average_close(ticker, days=days)
    print(f"  {days}일 평균 종가: {result}")

# 수기 검증
manual_prices = [45.93, 46.83, 49.35, 49.40, 49.39]
manual_avg = round(sum(manual_prices) / len(manual_prices), 2)
actual_avg = deps.market_indicator_repo.get_average_close(ticker, days=5)

print(f"\n[검증]")
print(f"  수기 종가: {manual_prices}")
print(f"  수기 평균: {manual_avg}")
print(f"  실제 조회: {actual_avg}")
print(f"  일치 여부: {'✅ 일치' if manual_avg == actual_avg else '❌ 불일치'}")
