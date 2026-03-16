import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.dependencies import init_dependencies
from usecase.trading_usecase import TradingUsecase

# 의존성 초기화 (test_mode=True: 실제 주문 X)
deps = init_dependencies(test_mode=True)

# bot_info 0번째 조회
all_bots = deps.bot_info_repo.find_all()
if not all_bots:
    print("bot_info가 없습니다")
    sys.exit(1)

bot_info = all_bots[0]
print(f"bot_info: {bot_info.name} / {bot_info.symbol} / seed={bot_info.seed}")

# TradingUsecase 생성
usecase = TradingUsecase(
    bot_info_repo=deps.bot_info_repo,
    trade_repo=deps.trade_repo,
    history_repo=deps.history_repo,
    order_repo=deps.order_repo,
    exchange_repo=deps.exchange_repo,
    message_repo=deps.message_repo,
)

# execute_closing_buy 호출
seed = bot_info.seed
print(f"execute_closing_buy 호출: seed={seed}")
usecase.execute_closing_buy(bot_info, seed)
print("완료")
