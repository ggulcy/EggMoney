"""전체 플로우 테스트 - TradingUsecase + OrderUsecase"""
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
from domain.value_objects.trade_type import TradeType


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

    # Service 생성 (test_mode=True)
    hantoo_service = HantooService(test_mode=True)
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

    return trading_usecase, order_usecase, bot_info_repo, trade_repo, history_repo, order_repo


def print_db_state(label, trade_repo, history_repo, order_repo, bot_name):
    """DB 상태 출력"""
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")

    # Trade 조회
    trade = trade_repo.find_by_name(bot_name)
    if trade:
        print(f"\n📊 Trade:")
        print(f"  - 종목: {trade.symbol}")
        print(f"  - 평단가: ${trade.purchase_price:,.2f}")
        print(f"  - 수량: {trade.amount:,.0f}주")
        print(f"  - 총액: ${trade.total_price:,.2f}")
    else:
        print(f"\n📊 Trade: 없음")

    # Order 조회
    order = order_repo.find_by_name(bot_name)
    if order:
        print(f"\n📝 Order:")
        print(f"  - 타입: {order.order_type.value}")
        print(f"  - 진행: {order.trade_count}/{order.total_count}")
        print(f"  - 남은 금액/수량: {order.remain_value:,.2f}")
        print(f"  - 거래 결과: {len(order.trade_result_list) if order.trade_result_list else 0}개")
    else:
        print(f"\n📝 Order: 없음")

    # History 조회 (최근 3개)
    all_history = history_repo.find_by_name_all(bot_name)
    if all_history:
        print(f"\n📜 History (최근 3개 / 전체 {len(all_history)}개):")
        for hist in all_history[:3]:
            print(f"  - {hist.trade_type.value}: ${hist.buy_price:.2f} → ${hist.sell_price:.2f} | 수익: ${hist.profit:,.2f} ({hist.profit_rate*100:.1f}%)")
    else:
        print(f"\n📜 History: 없음")


def test_buy_flow():
    """매수 플로우 테스트"""
    print("\n" + "="*60)
    print("💰 매수 플로우 테스트")
    print("="*60)

    trading_usecase, order_usecase, bot_info_repo, trade_repo, history_repo, order_repo = setup()

    # 테스트할 봇
    bot_name = "TQ_1"
    bot_info = bot_info_repo.find_by_name(bot_name)
    if not bot_info:
        print(f"❌ {bot_name} 조회 실패")
        return

    # [1] DB 상태 확인 (전)
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # [2] 매수 주문서 생성
    print(f"\n{'='*60}")
    print(f"📝 [2단계] 매수 주문서 생성")
    print(f"{'='*60}")
    seed = 500.0  # 500$ 매수
    order_usecase.create_buy_order(bot_info, seed, TradeType.BUY)

    # DB 상태 확인
    print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

    # [3] TWAP 주문 실행 (1차)
    print(f"\n{'='*60}")
    print(f"🔄 [3단계] TWAP 주문 실행 (1차)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인
    print_db_state("📸 [3단계] 1차 실행 후", trade_repo, history_repo, order_repo, bot_name)

    # [4] TWAP 주문 실행 (2차)
    print(f"\n{'='*60}")
    print(f"🔄 [4단계] TWAP 주문 실행 (2차)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인
    print_db_state("📸 [4단계] 2차 실행 후", trade_repo, history_repo, order_repo, bot_name)

    # [5] TWAP 주문 실행 (3차 - 완료)
    print(f"\n{'='*60}")
    print(f"🔄 [5단계] TWAP 주문 실행 (3차 - 완료)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인 (최종)
    print_db_state("📸 [5단계] 최종 상태 (완료)", trade_repo, history_repo, order_repo, bot_name)

    print(f"\n{'='*60}")
    print(f"✅ 매수 플로우 테스트 완료")
    print(f"{'='*60}")


def test_sell_flow():
    """매도 플로우 테스트"""
    print("\n" + "="*60)
    print("💸 매도 플로우 테스트")
    print("="*60)

    trading_usecase, order_usecase, bot_info_repo, trade_repo, history_repo, order_repo = setup()

    # 테스트할 봇
    bot_name = "TQ_1"
    bot_info = bot_info_repo.find_by_name(bot_name)
    if not bot_info:
        print(f"❌ {bot_name} 조회 실패")
        return

    # [1] DB 상태 확인 (전)
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 보유량 확인
    total_amount = trade_repo.get_total_amount(bot_name)
    if total_amount == 0:
        print("\n⚠️ 보유 주식이 없어 매도 테스트를 건너뜁니다")
        return

    # [2] 매도 주문서 생성 (1/4 매도)
    print(f"\n{'='*60}")
    print(f"📝 [2단계] 매도 주문서 생성 (1/4)")
    print(f"{'='*60}")
    sell_amount = int(total_amount * 0.25)
    order_usecase.create_sell_order(bot_info, sell_amount, TradeType.SELL_1_4)

    # DB 상태 확인
    print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

    # [3] TWAP 주문 실행 (1차)
    print(f"\n{'='*60}")
    print(f"🔄 [3단계] TWAP 주문 실행 (1차)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인
    print_db_state("📸 [3단계] 1차 실행 후", trade_repo, history_repo, order_repo, bot_name)

    # [4] TWAP 주문 실행 (2차)
    print(f"\n{'='*60}")
    print(f"🔄 [4단계] TWAP 주문 실행 (2차)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인
    print_db_state("📸 [4단계] 2차 실행 후", trade_repo, history_repo, order_repo, bot_name)

    # [5] TWAP 주문 실행 (3차 - 완료)
    print(f"\n{'='*60}")
    print(f"🔄 [5단계] TWAP 주문 실행 (3차 - 완료)")
    print(f"{'='*60}")
    order_usecase.execute_order(bot_info)

    # DB 상태 확인 (최종)
    print_db_state("📸 [5단계] 최종 상태 (완료)", trade_repo, history_repo, order_repo, bot_name)

    print(f"\n{'='*60}")
    print(f"✅ 매도 플로우 테스트 완료")
    print(f"{'='*60}")


if __name__ == "__main__":
    # 매수 플로우 테스트
    test_buy_flow()

    # 매도 플로우 테스트
    test_sell_flow()
