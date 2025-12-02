"""완전한 거래 플로우 테스트 - trade_job() + twap_job() 통합

테스트 케이스:
1. 첫 구매 (평단가 없음)
2. 일반 매수 (조건 만족)
3. 급락 시 매수 (시드 조정)
4. 1/4 매도 (%지점가만 돌파)
5. 3/4 매도 (익절가만 돌파)
6. 전체 매도 (익절가 + %지점가 돌파)
7. 손절 매도 (T >= Max-1)
"""
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
from domain.value_objects.trade_type import TradeType


def setup():
    """테스트 환경 설정"""
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

    # TradingJobs 생성
    trading_jobs = TradingJobs(
        trading_usecase=trading_usecase,
        order_usecase=order_usecase,
        bot_info_repo=bot_info_repo,
        order_repo=order_repo
    )

    return (trading_jobs, trading_usecase, order_usecase,
            bot_info_repo, trade_repo, history_repo, order_repo)


def print_db_state(label, trade_repo, history_repo, order_repo, bot_name):
    """DB 상태 출력"""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

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
    else:
        print(f"\n📝 Order: 없음")

    # History 조회 (최근 3개)
    all_history = history_repo.find_by_name_all(bot_name)
    if all_history:
        print(f"\n📜 History (최근 3개 / 전체 {len(all_history)}개):")
        for hist in all_history[:3]:
            profit_pct = hist.profit_rate * 100
            print(f"  - {hist.trade_type.value}: ${hist.buy_price:.2f} → ${hist.sell_price:.2f} "
                  f"| 수익: ${hist.profit:,.2f} ({profit_pct:.1f}%)")
    else:
        print(f"\n📜 History: 없음")


def execute_full_twap(trading_jobs, order_usecase, bot_name):
    """TWAP 주문을 완료까지 실행"""
    order_repo = trading_jobs.order_repo

    while True:
        order = order_repo.find_by_name(bot_name)
        if not order:
            break

        # TWAP 실행
        trading_jobs.twap_job()

        # 주문 완료 확인
        order = order_repo.find_by_name(bot_name)
        if not order:
            print(f"✅ TWAP 주문 완료")
            break


def test_case_1_first_buy():
    """케이스 1: 첫 구매 (평단가 없음)"""
    print("\n" + "="*70)
    print("테스트 케이스 1: 첫 구매 (평단가 없음)")
    print("="*70)

    (trading_jobs, trading_usecase, order_usecase,
     bot_info_repo, trade_repo, history_repo, order_repo) = setup()

    bot_name = "TQ_1"
    bot_info = bot_info_repo.find_by_name(bot_name)
    if not bot_info:
        print(f"❌ {bot_name} 봇이 없습니다.")
        return

    # 0. 기존 Trade, Order, 오늘 History 삭제 (첫 구매 상황 만들기)
    print(f"\n{'='*70}")
    print("📝 [준비] 기존 Trade/Order/History 정리 - 첫 구매 상황 만들기")
    print(f"{'='*70}")

    existing_trade = trade_repo.find_by_name(bot_name)
    if existing_trade:
        trade_repo.delete_by_name(bot_name)
        print(f"✅ 기존 Trade 삭제: {existing_trade.symbol} {existing_trade.amount}주")

    existing_order = order_repo.find_by_name(bot_name)
    if existing_order:
        order_repo.delete_order(bot_name)
        print(f"✅ 기존 Order 삭제")

    # 오늘 History 모두 삭제 (오늘 매도 기록이 있으면 매수를 건너뜀)
    deleted_count = 0
    while True:
        today_history = history_repo.find_today_by_name(bot_name)
        if not today_history:
            break
        history_repo.delete(bot_name, today_history.date_added)
        deleted_count += 1
    if deleted_count > 0:
        print(f"✅ 오늘 History 삭제: {deleted_count}개")

    # 1. 초기 상태 확인
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 2. TradingUsecase로 첫 구매 판단 + OrderUsecase로 주문서 생성
    print(f"\n{'='*70}")
    print("📝 [2단계] 첫 구매 판단 + 주문서 생성")
    print(f"{'='*70}")

    # 디버깅: 오늘 매도 기록 체크
    today_hist = history_repo.find_today_by_name(bot_name)
    has_sell_order = order_repo.has_sell_order_today(bot_name)
    print(f"🔍 디버그:")
    print(f"  - 오늘 History: {'있음' if today_hist else '없음'}")
    print(f"  - 오늘 Sell Order: {'있음' if has_sell_order else '없음'}")

    result = trading_usecase.execute_trading(bot_info)
    if result:
        trade_type, value = result
        print(f"✅ 매수 판단: {trade_type.value}, 시드: ${value:,.2f}")
        if trade_type.is_buy():
            order_usecase.create_buy_order(bot_info, value, trade_type)
    else:
        print(f"❌ 매수 조건 불충족")
        return

    print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

    # 3. TWAP 주문 직접 실행
    print(f"\n{'='*70}")
    print("🔄 [3단계] TWAP 주문 직접 실행")
    print(f"{'='*70}")

    order = order_repo.find_by_name(bot_name)
    count = 0
    while order:
        count += 1
        print(f"\n[TWAP {count}회차] 남은 횟수: {order.trade_count}/{order.total_count}")
        order_usecase.execute_order(bot_info)

        order = order_repo.find_by_name(bot_name)
        if not order:
            print(f"✅ TWAP 주문 완료 (총 {count}회)")
            break

    print_db_state("📸 [3단계] TWAP 완료 후", trade_repo, history_repo, order_repo, bot_name)

    print(f"\n{'='*70}")
    print(f"✅ 케이스 1 완료: 첫 구매")
    print(f"{'='*70}")


def test_case_2_normal_buy():
    """케이스 2: 일반 매수 (조건 만족)"""
    print("\n" + "="*70)
    print("테스트 케이스 2: 일반 매수 (조건 만족)")
    print("="*70)

    (trading_jobs, trading_usecase, order_usecase,
     bot_info_repo, trade_repo, history_repo, order_repo) = setup()

    bot_name = "TQ_1"  # 이미 평단가가 있는 봇

    # 1. 초기 상태 확인
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 2. trade_job 실행
    print(f"\n{'='*70}")
    print("📝 [2단계] trade_job() 실행 - 매수 조건 판단")
    print(f"{'='*70}")

    bot_info = bot_info_repo.find_by_name(bot_name)
    if not bot_info:
        print(f"❌ {bot_name} 봇이 없습니다.")
        return

    result = trading_usecase.execute_trading(bot_info)
    if result:
        trade_type, value = result
        if trade_type.is_buy():
            order_usecase.create_buy_order(bot_info, value, trade_type)
            print(f"✅ 매수 주문서 생성: ${value:,.2f}")
        else:
            print(f"⚠️ 매도 주문서 생성됨 (예상과 다름)")
    else:
        print(f"⚠️ 매수 조건 불충족")

    print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

    # 3. twap_job 실행
    order = order_repo.find_by_name(bot_name)
    if order and order.order_type.value == "Buy":
        print(f"\n{'='*70}")
        print("🔄 [3단계] twap_job() 실행 - TWAP 주문 완료까지")
        print(f"{'='*70}")

        execute_full_twap(trading_jobs, order_usecase, bot_name)

        print_db_state("📸 [3단계] TWAP 완료 후", trade_repo, history_repo, order_repo, bot_name)


def test_case_3_sell_1_4():
    """케이스 3: 1/4 매도 (%지점가만 돌파) - 직접 실행"""
    print("\n" + "="*70)
    print("테스트 케이스 3: 1/4 매도 (%지점가만 돌파)")
    print("="*70)

    (trading_jobs, trading_usecase, order_usecase,
     bot_info_repo, trade_repo, history_repo, order_repo) = setup()

    bot_name = "TQ_1"

    # 1. 초기 상태 확인
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 2. 강제로 1/4 매도 주문서 생성
    print(f"\n{'='*70}")
    print("📝 [2단계] 1/4 매도 주문서 생성 (OrderUsecase)")
    print(f"{'='*70}")

    total_amount = trade_repo.get_total_amount(bot_name)
    if total_amount > 0:
        sell_amount = int(total_amount * 0.25)
        bot_info = bot_info_repo.find_by_name(bot_name)

        order_usecase.create_sell_order(bot_info, sell_amount, TradeType.SELL_1_4)
        print(f"✅ 1/4 매도 주문서 생성: {sell_amount}주")

        print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

        # 3. TWAP 주문 직접 실행 (is_trade_date 체크 건너뛰기)
        print(f"\n{'='*70}")
        print("🔄 [3단계] TWAP 주문 직접 실행 (OrderUsecase)")
        print(f"{'='*70}")

        # twap_job 대신 직접 execute_order 호출
        order = order_repo.find_by_name(bot_name)
        count = 0
        while order:
            count += 1
            print(f"\n[TWAP {count}회차] 남은 횟수: {order.trade_count}/{order.total_count}")
            order_usecase.execute_order(bot_info)

            order = order_repo.find_by_name(bot_name)
            if not order:
                print(f"✅ TWAP 주문 완료 (총 {count}회)")
                break

        print_db_state("📸 [3단계] TWAP 완료 후", trade_repo, history_repo, order_repo, bot_name)
    else:
        print("❌ 보유 주식이 없어 테스트를 건너뜁니다")


def test_case_4_sell_3_4():
    """케이스 4: 3/4 매도 (익절가만 돌파)"""
    print("\n" + "="*70)
    print("테스트 케이스 4: 3/4 매도 (익절가만 돌파)")
    print("="*70)

    (trading_jobs, trading_usecase, order_usecase,
     bot_info_repo, trade_repo, history_repo, order_repo) = setup()

    bot_name = "TQ_1"

    # 1. 초기 상태 확인
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 2. 강제로 3/4 매도 실행
    print(f"\n{'='*70}")
    print("📝 [2단계] 강제 3/4 매도 실행")
    print(f"{'='*70}")

    total_amount = trade_repo.get_total_amount(bot_name)
    if total_amount > 0:
        sell_amount = int(total_amount * 0.75)
        bot_info = bot_info_repo.find_by_name(bot_name)

        order_usecase.create_sell_order(bot_info, sell_amount, TradeType.SELL_3_4)
        print(f"✅ 3/4 매도 주문서 생성: {sell_amount}주")

        print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

        # 3. twap_job 실행
        print(f"\n{'='*70}")
        print("🔄 [3단계] twap_job() 실행 - TWAP 주문 완료까지")
        print(f"{'='*70}")

        execute_full_twap(trading_jobs, order_usecase, bot_name)

        print_db_state("📸 [3단계] TWAP 완료 후", trade_repo, history_repo, order_repo, bot_name)
    else:
        print("❌ 보유 주식이 없어 테스트를 건너뜁니다")


def test_case_5_sell_full():
    """케이스 5: 전체 매도 (익절가 + %지점가 돌파)"""
    print("\n" + "="*70)
    print("테스트 케이스 5: 전체 매도")
    print("="*70)

    (trading_jobs, trading_usecase, order_usecase,
     bot_info_repo, trade_repo, history_repo, order_repo) = setup()

    bot_name = "TQ_1"

    # 1. 초기 상태 확인
    print_db_state("📸 [1단계] 초기 상태", trade_repo, history_repo, order_repo, bot_name)

    # 2. 강제로 전체 매도 실행
    print(f"\n{'='*70}")
    print("📝 [2단계] 강제 전체 매도 실행")
    print(f"{'='*70}")

    total_amount = trade_repo.get_total_amount(bot_name)
    if total_amount > 0:
        bot_info = bot_info_repo.find_by_name(bot_name)

        order_usecase.create_sell_order(bot_info, int(total_amount), TradeType.SELL)
        print(f"✅ 전체 매도 주문서 생성: {int(total_amount)}주")

        print_db_state("📸 [2단계] 주문서 생성 후", trade_repo, history_repo, order_repo, bot_name)

        # 3. twap_job 실행
        print(f"\n{'='*70}")
        print("🔄 [3단계] twap_job() 실행 - TWAP 주문 완료까지")
        print(f"{'='*70}")

        execute_full_twap(trading_jobs, order_usecase, bot_name)

        print_db_state("📸 [3단계] TWAP 완료 후 (Trade 삭제됨)", trade_repo, history_repo, order_repo, bot_name)
    else:
        print("❌ 보유 주식이 없어 테스트를 건너뜁니다")


if __name__ == "__main__":
    # 각 케이스를 순차적으로 실행
    print("\n" + "🚀"*35)
    print("완전한 거래 플로우 통합 테스트 시작")
    print("🚀"*35)

    # 테스트 케이스 선택
    # test_case_1_first_buy()       # 첫 구매
    test_case_2_normal_buy()      # 일반 매수
    # test_case_3_sell_1_4()        # 1/4 매도
    # test_case_4_sell_3_4()        # 3/4 매도
    # test_case_5_sell_full()       # 전체 매도

    print("\n" + "🎉"*35)
    print("테스트 완료")
    print("🎉"*35)
