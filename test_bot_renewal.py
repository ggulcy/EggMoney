"""봇 리뉴얼 테스트 스크립트"""
from config.dependencies import init_dependencies
from usecase.bot_management_usecase import BotManagementUsecase

# 시장 단계 설정 (0=수비, 1=중립, 2=공격, 3=매우공격)
MARKET_STAGE = 1


def print_current_bots(deps):
    """현재 봇 정보 출력 (print_db 형식)"""
    bots = deps.bot_info_repo.find_all()

    print("=" * 80)
    print("📚 현재 봇 정보")
    print("=" * 80)

    if bots:
        print(f"\n🤖 BotInfo ({len(bots)}개):")
        for bot in bots:
            active_emoji = "✅" if bot.active else "⏸️"
            print(
                f"   {active_emoji} {bot.name} ({bot.symbol}): "
                f"Seed={bot.seed:,.0f}$ | PR={bot.profit_rate*100:.0f}% | "
                f"T_div={bot.t_div} | Max={bot.max_tier}T | "
                f"PointLoc={bot.point_loc.value} | "
                f"AddedSeed={bot.added_seed:,.0f}$"
            )
    else:
        print("⚠️ BotInfo가 없습니다.")
    print("=" * 80)
    print()


def print_renewal_preview(preview, current_bots):
    """리뉴얼 미리보기 출력 (변경사항 위주)"""
    if preview is None:
        print("⚠️ 리뉴얼 결과가 없습니다.")
        return

    stage_names = {0: "수비적", 1: "중립", 2: "공격적", 3: "매우공격적"}
    stage_name = stage_names[preview["market_stage"]]

    print("=" * 80)
    print(f"🔄 리뉴얼 미리보기 - {stage_name} 모드 (단계 {preview['market_stage']})")
    print("=" * 80)

    print(f"\n📊 예산 배분:")
    print(f"   총 예산:        ${preview['total_budget']:,.0f}")
    print(f"   현금 보유:      ${preview['cash_reserve']:,.0f} ({preview['cash_reserve']/preview['total_budget']*100:.0f}%)")
    print(f"   투자 금액:      ${preview['investable']:,.0f}")

    print(f"\n🤖 BotInfo ({len(preview['bots'])}개) - 변경사항:")

    current_total_seed = 0
    new_total_seed = 0

    for i, (current_bot, new_bot) in enumerate(zip(current_bots, preview['bots'])):
        current_total_seed += current_bot.seed
        new_total_seed += new_bot['seed']

        changes = []

        # Seed 변경
        if abs(current_bot.seed - new_bot['seed']) > 0.01:
            changes.append(f"Seed={current_bot.seed:,.0f}$→{new_bot['seed']:,.0f}$")
        else:
            changes.append(f"Seed={new_bot['seed']:,.0f}$")

        # Profit Rate 변경
        if abs(current_bot.profit_rate - new_bot['profit_rate']) > 0.001:
            changes.append(f"PR={current_bot.profit_rate*100:.0f}%→{new_bot['profit_rate']*100:.0f}%")
        else:
            changes.append(f"PR={new_bot['profit_rate']*100:.0f}%")

        # T_div는 항상 동일 (출력만)
        changes.append(f"T_div={current_bot.t_div}")

        # Max Tier 변경
        if current_bot.max_tier != new_bot['max_tier']:
            changes.append(f"Max={current_bot.max_tier}T→{new_bot['max_tier']}T")
        else:
            changes.append(f"Max={new_bot['max_tier']}T")

        # PointLoc 변경
        if current_bot.point_loc.value != new_bot['point_loc']:
            changes.append(f"PointLoc={current_bot.point_loc.value}→{new_bot['point_loc']}")
        else:
            changes.append(f"PointLoc={new_bot['point_loc']}")

        # Level 정보 (새로 추가)
        changes.append(f"Level={new_bot['level']}({new_bot['level_name']})")

        active_emoji = "✅" if current_bot.active else "⏸️"
        print(f"   {active_emoji} {new_bot['name']} ({new_bot['symbol']}): {' | '.join(changes)}")

    # 총 1회 시드 변경사항
    print(f"\n💰 총 1회 시드:")
    if abs(current_total_seed - new_total_seed) > 0.01:
        seed_change = new_total_seed - current_total_seed
        change_emoji = "📈" if seed_change > 0 else "📉"
        print(f"   {change_emoji} ${current_total_seed:,.0f} → ${new_total_seed:,.0f} (변경: {seed_change:+,.0f}$)")
    else:
        print(f"   💵 ${new_total_seed:,.0f} (변경 없음)")

    # 최대 투자금 계산 (각 봇의 seed × max_tier 합산)
    current_max_investment = sum(bot.seed * bot.max_tier for bot in current_bots)
    new_max_investment = sum(bot['seed'] * bot['max_tier'] for bot in preview['bots'])

    print(f"\n💎 최대 투자금:")
    if abs(current_max_investment - new_max_investment) > 0.01:
        investment_change = new_max_investment - current_max_investment
        change_emoji = "📈" if investment_change > 0 else "📉"
        print(f"   {change_emoji} ${current_max_investment:,.0f} → ${new_max_investment:,.0f} (변경: {investment_change:+,.0f}$)")
    else:
        print(f"   💵 ${new_max_investment:,.0f} (변경 없음)")

    print("=" * 80)


if __name__ == "__main__":
    # 의존성 초기화
    deps = init_dependencies(test_mode=True)

    # 현재 봇 정보 가져오기
    current_bots = deps.bot_info_repo.find_all()

    # 현재 봇 정보 출력
    print_current_bots(deps)

    # Usecase 초기화
    bot_usecase = BotManagementUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo
    )

    # 봇 리뉴얼 미리보기 조회
    preview = bot_usecase.preview_bot_renewal(MARKET_STAGE)

    # 미리보기 출력
    print_renewal_preview(preview, current_bots)
