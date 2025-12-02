"""TradingUsecase 테스트"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import item
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
    SQLAlchemyOrderRepository
)
from data.external.hantoo.hantoo_service import HantooService
from usecase import TradingUsecase, MarketAnalysisUsecase


def setup():
    """테스트 환경 설정"""
    # SessionFactory 초기화 (item.admin이 자동으로 사용됨)
    session_factory = SessionFactory()
    session = session_factory.create_session()

    # Repository 생성
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    order_repo = SQLAlchemyOrderRepository(session)

    # Service 생성
    hantoo_service = HantooService(test_mode=True)  # 테스트 모드
    market_analysis_usecase = MarketAnalysisUsecase()

    # Usecase 생성
    trading_usecase = TradingUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        order_repo=order_repo,
        hantoo_service=hantoo_service,
        market_analysis_usecase=market_analysis_usecase
    )

    return trading_usecase, bot_info_repo


def test_execute_trading():
    """매도 → 매수 실행 테스트"""
    print("\n========== 매도 → 매수 실행 테스트 ==========")
    trading_usecase, bot_info_repo = setup()

    # 테스트할 봇 이름
    bot_name = "TQ_1"

    bot_info = bot_info_repo.find_by_name(bot_name)
    if bot_info:
        print(f"✅ {bot_name} 조회 성공")
        print(f"  Symbol: {bot_info.symbol}")
        print(f"  Active: {bot_info.active}")
        print(f"  Skip Sell: {bot_info.skip_sell}")
        print("\n매도 → 매수 실행 중...")

        trading_usecase.execute_trading(bot_info)
        print("\n✅ 매도 → 매수 실행 완료")
    else:
        print(f"❌ {bot_name} 조회 실패")


def test_force_sell():
    """강제 매도 테스트"""
    print("\n========== 강제 매도 테스트 ==========")
    trading_usecase, bot_info_repo = setup()

    # 테스트할 봇 이름
    bot_name = "TQ_1"
    sell_ratio = 50.0  # 50% 매도

    bot_info = bot_info_repo.find_by_name(bot_name)
    if bot_info:
        print(f"✅ {bot_name} 조회 성공")
        print(f"  Symbol: {bot_info.symbol}")
        print(f"\n{sell_ratio}% 강제 매도 실행 중...")

        trading_usecase.force_sell(bot_info, sell_ratio)
        print("\n✅ 강제 매도 완료")
    else:
        print(f"❌ {bot_name} 조회 실패")


if __name__ == "__main__":
    # 각 함수는 독립적으로 실행 가능
    test_execute_trading()
    # test_force_sell()
