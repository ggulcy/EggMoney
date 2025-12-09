"""동적 시드 기능 테스트"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import item
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository
)
from data.external.hantoo.hantoo_service import HantooService
from usecase import BotManagementUsecase


def setup():
    """테스트 환경 설정"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    hantoo_service = HantooService(test_mode=item.is_test)

    bot_usecase = BotManagementUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        hantoo_service=hantoo_service,
    )

    return bot_usecase


def test_check_and_apply_dynamic_seed():
    """check_and_apply_dynamic_seed 테스트"""
    print("\n" + "=" * 60)
    print("동적 시드 적용 테스트")
    print("=" * 60)
    print(f"Admin: {item.admin}")
    print(f"Test Mode: {item.is_test}")
    print("=" * 60)

    bot_usecase = setup()

    # 모든 활성 봇 정보 출력
    bot_data = bot_usecase.get_all_bot_info_with_t()
    print(f"\n활성 봇 목록 ({len(bot_data)}개):")
    for data in bot_data:
        bot = data['bot_info']
        print(f"  - {bot.name}: seed=${bot.seed}, dynamic_seed_max=${bot.dynamic_seed_max}, added_seed=${bot.added_seed}")

    print("\n" + "-" * 60)
    print("check_and_apply_dynamic_seed() 호출...")
    print("-" * 60)

    # 동적 시드 적용
    bot_usecase.check_and_apply_dynamic_seed()

    print("\n" + "-" * 60)
    print("적용 후 봇 정보:")
    print("-" * 60)

    # 적용 후 봇 정보 다시 조회
    bot_data = bot_usecase.get_all_bot_info_with_t()
    for data in bot_data:
        bot = data['bot_info']
        print(f"  - {bot.name}: seed=${bot.seed}, dynamic_seed_max=${bot.dynamic_seed_max}, added_seed=${bot.added_seed}, total=${bot.get_total_seed()}")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


def test_apply_single_bot(bot_name: str):
    """단일 봇에 대해 동적 시드 적용 테스트 (디버그 포함)"""
    print("\n" + "=" * 60)
    print(f"단일 봇 동적 시드 테스트: {bot_name}")
    print("=" * 60)

    bot_usecase = setup()
    hantoo_service = bot_usecase.hantoo_service

    bot_info = bot_usecase.get_bot_info_by_name(bot_name)
    if not bot_info:
        print(f"봇을 찾을 수 없습니다: {bot_name}")
        return

    print(f"\n[봇 정보]")
    print(f"  - seed: ${bot_info.seed}")
    print(f"  - dynamic_seed_max: ${bot_info.dynamic_seed_max}")
    print(f"  - added_seed: ${bot_info.added_seed}")
    print(f"  - total_seed: ${bot_info.get_total_seed()}")
    print(f"  - active: {bot_info.active}")

    # 조건 체크
    print(f"\n[조건 체크]")
    if bot_info.dynamic_seed_max <= 0:
        print(f"  ❌ dynamic_seed_max({bot_info.dynamic_seed_max}) <= 0 → 기능 비활성화")
        return
    else:
        print(f"  ✅ dynamic_seed_max({bot_info.dynamic_seed_max}) > 0")

    if bot_info.seed >= bot_info.dynamic_seed_max:
        print(f"  ❌ seed({bot_info.seed}) >= dynamic_seed_max({bot_info.dynamic_seed_max}) → 적용 불필요")
        return
    else:
        print(f"  ✅ seed({bot_info.seed}) < dynamic_seed_max({bot_info.dynamic_seed_max})")

    # 가격 조회
    prev_close = hantoo_service.get_prev_price(bot_info.symbol)
    current_price = hantoo_service.get_price(bot_info.symbol)
    print(f"\n[가격 정보] {bot_info.symbol}")
    print(f"  - 전일 종가: ${prev_close}")
    print(f"  - 현재가: ${current_price}")

    if prev_close and current_price and prev_close > 0:
        drop_rate = (prev_close - current_price) / prev_close
        print(f"  - 하락률: {drop_rate * 100:.2f}%")
        if drop_rate < 0.03:
            print(f"  ❌ 하락률({drop_rate * 100:.2f}%) < 3% → 적용 안함")
        else:
            print(f"  ✅ 하락률({drop_rate * 100:.2f}%) >= 3% → 적용 대상")

    print("\n[apply_dynamic_seed() 호출]")
    result = bot_usecase.apply_dynamic_seed(bot_info)

    if result:
        print(f"  ✅ 적용 성공:")
        print(f"     - old_seed: ${result['old_seed']}")
        print(f"     - new_seed: ${result['new_seed']}")
        print(f"     - drop_rate: {result['drop_rate']:.2f}%")
        print(f"     - increase_rate: {result['increase_rate']:.1f}%")
    else:
        print("  ❌ 적용 안됨")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 단일 봇 테스트 (디버그용) - 봇 이름 변경해서 사용
    test_apply_single_bot("TQ_1")

    # 전체 테스트
    # test_check_and_apply_dynamic_seed()
