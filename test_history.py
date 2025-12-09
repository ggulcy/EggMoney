"""History Entity 및 Repository 테스트"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.history import History
from domain.value_objects.trade_type import TradeType
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories.history_repository_impl import SQLAlchemyHistoryRepository


def test_history_creation():
    """History 생성 및 검증 테스트"""
    print("=" * 60)
    print("History 생성 및 검증 테스트")
    print("=" * 60)

    # 정상 생성
    print("\n[정상 생성]")
    history = History(
        date_added=datetime(2024, 1, 1, 10, 0, 0),
        trade_date=datetime(2024, 1, 5, 15, 30, 0),
        trade_type=TradeType.SELL,
        name="bot1",
        symbol="SOXL",
        buy_price=50.0,
        sell_price=60.0,
        amount=10,
        profit=100.0,
        profit_rate=0.2  # 20%
    )
    print(f"✅ History 생성 성공: {history}")
    print(f"수익금: {history.get_profit_dollar()}")
    print(f"수익률: {history.get_profit_rate_percent()}")
    print(f"수익 여부: {history.is_profitable()}")

    # 검증 실패 테스트
    print("\n[검증 실패 테스트]")
    try:
        invalid_history = History(
            date_added=datetime.now(),
            trade_date=datetime.now(),
            trade_type=TradeType.SELL,
            name="",  # 빈 이름
            symbol="SOXL",
            buy_price=50.0,
            sell_price=60.0,
            amount=10,
            profit=100.0,
            profit_rate=0.2
        )
        print("❌ 검증 실패: 빈 이름이 허용되었습니다")
    except ValueError as e:
        print(f"✅ 검증 성공: {e}")

    print("\n✅ History 생성 및 검증 테스트 완료\n")


def test_history_repository():
    """History Repository 테스트"""
    print("=" * 60)
    print("History Repository 테스트")
    print("=" * 60)

    # SessionFactory 생성
    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyHistoryRepository(session)

    # 테스트 데이터 생성
    print("\n[테스트 데이터 생성]")
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    history1 = History(
        date_added=yesterday,
        trade_date=now,
        trade_type=TradeType.SELL,
        name="bot1",
        symbol="SOXL",
        buy_price=50.0,
        sell_price=60.0,
        amount=10,
        profit=100.0,
        profit_rate=0.2
    )

    history2 = History(
        date_added=yesterday,
        trade_date=now,
        trade_type=TradeType.SELL_1_4,
        name="bot1",
        symbol="TQQQ",
        buy_price=40.0,
        sell_price=45.0,
        amount=10,
        profit=50.0,
        profit_rate=0.125
    )

    # 저장
    print("\n[히스토리 저장]")
    repo.save(history1)
    repo.save(history2)
    print("✅ 2개의 히스토리 저장 완료")

    # 조회
    print("\n[name으로 조회]")
    found = repo.find_by_name("bot1")
    print(f"찾은 히스토리: {found}")
    assert found is not None, "조회 실패"
    print("✅ name으로 조회 성공")

    # 전체 조회
    print("\n[전체 조회]")
    all_history = repo.find_all()
    print(f"전체 히스토리 개수: {len(all_history)}")
    for h in all_history:
        print(f"  - {h.name}: {h.symbol}, Profit: {h.get_profit_dollar()}")
    print("✅ 전체 조회 성공")

    # 총 수익 계산 (매도 거래만)
    print("\n[총 매도 수익 계산]")
    total_profit = repo.get_total_sell_profit()
    print(f"전체 매도 총 수익: ${total_profit:,.2f}")
    assert total_profit == 150.0, "총 수익 계산 오류"

    total_by_name = repo.get_total_sell_profit_by_name("bot1")
    print(f"bot1 매도 총 수익: ${total_by_name:,.2f}")
    assert total_by_name == 150.0, "name별 총 수익 계산 오류"

    total_by_symbol = repo.get_total_sell_profit_by_symbol("SOXL")
    print(f"SOXL 매도 총 수익: ${total_by_symbol:,.2f}")
    assert total_by_symbol == 100.0, "symbol별 총 수익 계산 오류"
    print("✅ 총 매도 수익 계산 성공")

    session.close()
    print("\n✅ History Repository 테스트 완료\n")


def test_year_month_queries():
    """연월별 조회 테스트"""
    print("=" * 60)
    print("연월별 조회 테스트")
    print("=" * 60)

    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyHistoryRepository(session)

    # 현재 연월
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    print(f"\n[{current_year}년 {current_month}월 히스토리 조회]")
    monthly_history = repo.find_by_year_month(current_year, current_month)
    print(f"이번 달 히스토리: {len(monthly_history)}개")
    for h in monthly_history:
        print(f"  - {h.name}: {h.symbol}, {h.get_profit_dollar()}")

    # 월별 매도 수익
    print(f"\n[{current_year}년 월별 매도 수익]")
    monthly_profit = repo.get_monthly_sell_profit_by_year(current_year)
    for month, profit in monthly_profit:
        print(f"  {month}월: ${profit:,.2f}")

    # 연도별 매도 총 수익
    print(f"\n[{current_year}년 매도 총 수익]")
    yearly_profit = repo.get_total_sell_profit_by_year(current_year)
    print(f"{current_year}년 매도 총 수익: ${yearly_profit:,.2f}")

    # 연도 목록
    print("\n[거래 연도 목록]")
    years = repo.get_years_from_sell_date()
    print(f"거래 연도: {years}")

    session.close()
    print("\n✅ 연월별 조회 테스트 완료\n")


def test_delete_operations():
    """삭제 테스트"""
    print("=" * 60)
    print("삭제 테스트")
    print("=" * 60)

    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyHistoryRepository(session)

    # 테스트용 히스토리 생성
    print("\n[테스트용 히스토리 생성]")
    test_history = History(
        date_added=datetime.now(),
        trade_date=datetime.now(),
        trade_type=TradeType.SELL,
        name="test_bot",
        symbol="TEST",
        buy_price=10.0,
        sell_price=15.0,
        amount=10,
        profit=50.0,
        profit_rate=0.5
    )
    repo.save(test_history)
    print("✅ 테스트 히스토리 생성 완료")

    # name으로 삭제
    print("\n[name으로 삭제]")
    repo.delete_by_name("test_bot")
    found = repo.find_by_name("test_bot")
    assert found is None, "삭제 실패"
    print("✅ name으로 삭제 성공")

    session.close()
    print("\n✅ 삭제 테스트 완료\n")


if __name__ == "__main__":
    test_history_creation()
    test_history_repository()
    test_year_month_queries()
    test_delete_operations()

    print("=" * 60)
    print("✅ 모든 History 테스트 통과!")
    print("=" * 60)
