"""BotManagementUsecase 테스트"""
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
from usecase import BotManagementUsecase


def setup():
    """테스트 환경 설정"""
    # SessionFactory 초기화 (item.admin이 자동으로 사용됨)
    session_factory = SessionFactory()
    session = session_factory.create_session()

    # Repository 생성
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)

    # Usecase 생성
    bot_usecase = BotManagementUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo
    )

    return bot_usecase


def test_get_all_bot_info_with_t():
    """모든 봇 정보 + T값 조회 테스트"""
    print("\n========== 모든 봇 정보 + T값 조회 ==========")
    bot_usecase = setup()

    bot_info_list = bot_usecase.get_all_bot_info_with_t()

    print(f"총 {len(bot_info_list)}개의 봇 정보")
    for item in bot_info_list:
        bot_info = item["bot_info"]
        t = item["t"]
        active_icon = "✅" if bot_info.active else "⏸️"
        print(f"{active_icon} {bot_info.name} ({bot_info.symbol}): T = {t:.2f} / {bot_info.max_tier}")


def test_check_bot_sync():
    """봇 조건 자동 조정 테스트"""
    print("\n========== 봇 조건 자동 조정 테스트 ==========")
    bot_usecase = setup()

    # SK 계정이면 스킵 메시지 출력
    if item.admin == item.BotAdmin.SK:
        print("SK 계정은 bot sync 체크를 하지 않습니다")
        return

    print("check_bot_sync() 실행 중...")
    bot_usecase.check_bot_sync()
    print("check_bot_sync() 완료")


def test_get_bot_info_by_name():
    """이름으로 봇 정보 조회 테스트"""
    print("\n========== 이름으로 봇 정보 조회 테스트 ==========")
    bot_usecase = setup()

    # 테스트할 봇 이름
    bot_name = "TQ_1"

    bot_info = bot_usecase.get_bot_info_by_name(bot_name)
    if bot_info:
        print(f"✅ {bot_name} 조회 성공")
        print(f"  Symbol: {bot_info.symbol}")
        print(f"  Seed: {bot_info.seed:,.0f}$")
        print(f"  Profit Rate: {bot_info.profit_rate * 100:.0f}%")
        print(f"  T Div: {bot_info.t_div}")
        print(f"  Max Tier: {bot_info.max_tier}")
        print(f"  Active: {bot_info.active}")
        print(f"  평단가 조건: {bot_info.is_check_buy_avr_price}")
        print(f"  %지점가 조건: {bot_info.is_check_buy_t_div_price}")
    else:
        print(f"❌ {bot_name} 조회 실패")


if __name__ == "__main__":
    # 각 함수는 독립적으로 실행 가능
    test_get_all_bot_info_with_t()
    # test_check_bot_sync()
    # test_get_bot_info_by_name()
