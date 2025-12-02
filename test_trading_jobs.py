"""TradingJobs 테스트"""
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
from usecase import TradingUsecase, OrderUsecase, MarketAnalysisUsecase
from presentation.scheduler import TradingJobs


def setup():
    """테스트 환경 설정"""
    # SessionFactory 초기화
    session_factory = SessionFactory()
    session = session_factory.create_session()

    # Repository 생성
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    order_repo = SQLAlchemyOrderRepository(session)

    # Service 생성
    hantoo_service = HantooService(test_mode=item.is_test)
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

    order_usecase = OrderUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        order_repo=order_repo,
        hantoo_service=hantoo_service
    )

    # TradingJobs 생성
    trading_jobs = TradingJobs(
        trading_usecase=trading_usecase,
        order_usecase=order_usecase,
        bot_info_repo=bot_info_repo,
        order_repo=order_repo
    )

    return trading_jobs, bot_info_repo, order_repo


def test_trade_job():
    """메인 거래 작업 테스트"""
    print("\n========== 메인 거래 작업 테스트 ==========")
    trading_jobs, bot_info_repo, order_repo = setup()

    # 거래 실행
    trading_jobs.trade_job()

    # 주문서 확인
    print("\n📝 생성된 주문서:")
    orders = order_repo.find_all()
    if orders:
        for order in orders:
            print(f"  - {order.name}: {order.order_type.value}, {order.trade_count}/{order.total_count}")
    else:
        print("  - 없음")


def test_twap_job():
    """TWAP 작업 테스트"""
    print("\n========== TWAP 작업 테스트 ==========")
    trading_jobs, bot_info_repo, order_repo = setup()

    # 주문서 있는지 확인
    orders = order_repo.find_all()
    if not orders:
        print("❌ 주문서가 없습니다. test_trade_job()을 먼저 실행하세요.")
        return

    print(f"📝 처리할 주문서: {len(orders)}개")
    for order in orders:
        print(f"  - {order.name}: {order.trade_count}/{order.total_count}")

    # TWAP 실행
    trading_jobs.twap_job()

    # 주문서 상태 확인
    print("\n📝 TWAP 실행 후:")
    orders = order_repo.find_all()
    if orders:
        for order in orders:
            print(f"  - {order.name}: {order.trade_count}/{order.total_count}")
    else:
        print("  - 모든 주문서 완료됨")


def test_force_sell():
    """강제 매도 테스트"""
    print("\n========== 강제 매도 테스트 ==========")
    trading_jobs, bot_info_repo, order_repo = setup()

    # 테스트할 봇
    bot_name = "TQ_1"
    sell_ratio = 25.0  # 25% 매도

    print(f"\n{bot_name} - {sell_ratio}% 강제 매도 실행")
    trading_jobs.force_sell_job(bot_name, sell_ratio)

    # 주문서 확인
    order = order_repo.find_by_name(bot_name)
    if order:
        print(f"\n✅ 주문서 생성 완료")
        print(f"  - 타입: {order.order_type.value}")
        print(f"  - 분할: {order.trade_count}/{order.total_count}")
        print(f"  - 남은 수량: {order.remain_value}")
    else:
        print("❌ 주문서 생성 실패 (또는 매도할 수량 없음)")


if __name__ == "__main__":
    # 각 함수를 개별적으로 실행 가능
    test_trade_job()
    # test_twap_job()
    # test_force_sell()
