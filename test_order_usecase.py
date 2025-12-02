"""OrderUsecase 테스트"""
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
from usecase import OrderUsecase
from domain.value_objects.trade_type import TradeType


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

    # Usecase 생성
    order_usecase = OrderUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        order_repo=order_repo,
        hantoo_service=hantoo_service
    )

    return order_usecase, bot_info_repo, order_repo


def test_create_buy_order():
    """매수 주문서 생성 테스트"""
    print("\n========== 매수 주문서 생성 테스트 ==========")
    order_usecase, bot_info_repo, order_repo = setup()

    # 테스트할 봇 이름
    bot_name = "TQ_1"

    bot_info = bot_info_repo.find_by_name(bot_name)
    if bot_info:
        print(f"✅ {bot_name} 조회 성공")
        print(f"  Symbol: {bot_info.symbol}")

        # 매수 주문서 생성
        seed = 1000.0  # 1000$ 매수
        trade_type = TradeType.BUY

        print(f"\n{seed}$ 매수 주문서 생성 중...")
        order_usecase.create_buy_order(bot_info, seed, trade_type)

        # 주문서 확인
        order = order_repo.find_by_name(bot_name)
        if order:
            print(f"\n✅ 주문서 생성 완료")
            print(f"  - 분할 회수: {order.trade_count}/{order.total_count}")
            print(f"  - 총 금액: {order.total_value:,.2f}$")
            print(f"  - 남은 금액: {order.remain_value:,.2f}$")
        else:
            print("❌ 주문서 생성 실패")
    else:
        print(f"❌ {bot_name} 조회 실패")


if __name__ == "__main__":
    test_create_buy_order()
