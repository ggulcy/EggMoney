"""
오늘의 거래 테스트 데이터 삽입 스크립트

실행 방법:
    python insert_test_data.py

주의:
    - 테스트용 가짜 데이터를 삽입합니다
    - 실제 운영 환경에서는 사용하지 마세요
"""
from datetime import datetime
from config.item import admin
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository
)
from domain.entities.trade import Trade
from domain.entities.history import History
from domain.value_objects.trade_type import TradeType


def insert_test_trades():
    """오늘 매수한 Trade 테스트 데이터 삽입"""
    session_factory = SessionFactory()
    session = session_factory.create_session()
    trade_repo = SQLAlchemyTradeRepository(session)

    now = datetime.now()

    # 테스트 Trade 데이터
    test_trades = [
        Trade(
            name="TEST_TQQQ",
            symbol="TQQQ",
            purchase_price=65.50,
            amount=10.0,
            trade_type=TradeType.BUY,
            total_price=655.0,
            date_added=datetime(2025, 12, 1, 9, 30),
            latest_date_trade=now  # 오늘 날짜!
        ),
        Trade(
            name="TEST_SOXL",
            symbol="SOXL",
            purchase_price=28.30,
            amount=15.0,
            trade_type=TradeType.BUY,
            total_price=424.5,
            date_added=datetime(2025, 12, 1, 10, 0),
            latest_date_trade=now  # 오늘 날짜!
        ),
        Trade(
            name="TEST_UPRO",
            symbol="UPRO",
            purchase_price=82.10,
            amount=8.0,
            trade_type=TradeType.BUY,
            total_price=656.8,
            date_added=datetime(2025, 12, 1, 11, 0),
            latest_date_trade=now  # 오늘 날짜!
        )
    ]

    print("📊 오늘 매수한 Trade 데이터 삽입 중...")
    for trade in test_trades:
        trade_repo.save(trade)
        print(f"  ✅ {trade.symbol}: ${trade.purchase_price} x {trade.amount} = ${trade.total_price}")

    print(f"\n✅ {len(test_trades)}개의 Trade 데이터 삽입 완료!")


def insert_test_histories():
    """오늘 매도한 History 테스트 데이터 삽입"""
    session_factory = SessionFactory()
    session = session_factory.create_session()
    history_repo = SQLAlchemyHistoryRepository(session)

    now = datetime.now()

    # 테스트 History 데이터
    test_histories = [
        History(
            date_added=datetime(2025, 11, 25, 9, 0),
            sell_date=now,  # 오늘 날짜!
            trade_type=TradeType.SELL,
            name="TEST_QQQ",
            symbol="QQQ",
            buy_price=450.20,
            sell_price=465.80,
            profit=156.0,  # (465.80 - 450.20) * 10
            profit_rate=0.0346  # 3.46%
        ),
        History(
            date_added=datetime(2025, 11, 28, 10, 0),
            sell_date=now,  # 오늘 날짜!
            trade_type=TradeType.SELL_3_4,
            name="TEST_SPY",
            symbol="SPY",
            buy_price=520.50,
            sell_price=532.10,
            profit=174.0,  # (532.10 - 520.50) * 15
            profit_rate=0.0223  # 2.23%
        ),
        History(
            date_added=datetime(2025, 12, 3, 11, 0),
            sell_date=now,  # 오늘 날짜!
            trade_type=TradeType.SELL,
            name="TEST_IWM",
            symbol="IWM",
            buy_price=210.30,
            sell_price=207.80,
            profit=-25.0,  # (207.80 - 210.30) * 10 = -25.0
            profit_rate=-0.0119  # -1.19%
        )
    ]

    print("\n📊 오늘 매도한 History 데이터 삽입 중...")
    for history in test_histories:
        history_repo.save(history)
        profit_sign = "+" if history.profit >= 0 else ""
        print(f"  ✅ {history.symbol}: ${history.buy_price} → ${history.sell_price} "
              f"(수익: {profit_sign}${history.profit:.2f}, {history.profit_rate*100:.2f}%)")

    print(f"\n✅ {len(test_histories)}개의 History 데이터 삽입 완료!")


def main():
    """메인 함수"""
    print("=" * 60)
    print("🧪 오늘의 거래 테스트 데이터 삽입 스크립트")
    print(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"👤 Admin: {admin.value}")
    print("=" * 60)
    print()

    try:
        # 1. 매수 데이터 삽입
        insert_test_trades()

        # 2. 매도 데이터 삽입
        insert_test_histories()

        print("\n" + "=" * 60)
        print("🎉 모든 테스트 데이터 삽입 완료!")
        print("=" * 60)
        print("\n💡 이제 브라우저에서 확인해보세요:")
        print("   http://localhost:5000/")
        print("\n🗑️  테스트 데이터 삭제 방법:")
        print("   - Trade: name이 'TEST_'로 시작하는 레코드 삭제")
        print("   - History: name이 'TEST_'로 시작하는 레코드 삭제")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
