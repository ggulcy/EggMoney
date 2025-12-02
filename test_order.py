"""Order Entity 및 Repository 테스트"""
import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.order import Order
from domain.value_objects.order_type import OrderType
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories.order_repository_impl import SQLAlchemyOrderRepository


def test_order_creation():
    """Order 생성 및 검증 테스트"""
    print("=" * 60)
    print("Order 생성 및 검증 테스트")
    print("=" * 60)

    # 정상 생성
    print("\n[정상 생성]")
    order = Order(
        name="bot1",
        date_added=datetime.now(),
        symbol="SOXL",
        trade_result_list=[
            {"amount": 10, "price": 50.0, "total": 500.0},
            {"amount": 5, "price": 55.0, "total": 275.0}
        ],
        order_type=OrderType.BUY,
        trade_count=2,
        total_count=5,
        remain_value=225.0,
        total_value=1000.0
    )
    print(f"✅ Order 생성 성공: {order}")
    print(f"완료율: {order.get_completion_percent()}")
    print(f"완료 여부: {order.is_completed()}")

    # Entity 메서드 테스트
    print("\n[Entity 메서드 테스트]")
    print(f"매수 주문: {order.is_buy_order()}")
    print(f"매도 주문: {order.is_sell_order()}")

    # 거래 결과 추가
    print("\n[거래 결과 추가]")
    order.add_trade_result({"amount": 3, "price": 52.0, "total": 156.0})
    print(f"거래 결과 개수: {len(order.trade_result_list)}")
    assert len(order.trade_result_list) == 3, "거래 결과 추가 실패"

    # 거래 횟수 증가
    print("\n[거래 횟수 증가]")
    order.increment_trade_count()
    print(f"거래 횟수: {order.trade_count}/{order.total_count}")
    assert order.trade_count == 3, "거래 횟수 증가 실패"

    # 검증 실패 테스트
    print("\n[검증 실패 테스트]")
    try:
        invalid_order = Order(
            name="",  # 빈 이름
            date_added=datetime.now(),
            symbol="SOXL",
            trade_result_list=[],
            order_type=OrderType.BUY,
            trade_count=0,
            total_count=5,
            remain_value=1000.0,
            total_value=1000.0
        )
        print("❌ 검증 실패: 빈 이름이 허용되었습니다")
    except ValueError as e:
        print(f"✅ 검증 성공: {e}")

    print("\n✅ Order 생성 및 검증 테스트 완료\n")


def test_order_repository():
    """Order Repository 테스트"""
    print("=" * 60)
    print("Order Repository 테스트")
    print("=" * 60)

    # SessionFactory 생성
    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyOrderRepository(session)

    # 테스트 데이터 생성
    print("\n[테스트 데이터 생성]")
    order1 = Order(
        name="bot1",
        date_added=datetime.now(),
        symbol="SOXL",
        trade_result_list=[
            {"amount": 10, "price": 50.0, "total": 500.0}
        ],
        order_type=OrderType.BUY,
        trade_count=1,
        total_count=3,
        remain_value=500.0,
        total_value=1000.0
    )

    order2 = Order(
        name="bot2",
        date_added=datetime.now(),
        symbol="TQQQ",
        trade_result_list=[],
        order_type=OrderType.SELL,
        trade_count=0,
        total_count=5,
        remain_value=2000.0,
        total_value=2000.0
    )

    # 저장
    print("\n[주문 저장]")
    repo.save(order1)
    repo.save(order2)
    print("✅ 2개의 주문 저장 완료")

    # 조회
    print("\n[name으로 조회]")
    found = repo.find_by_name("bot1")
    print(f"찾은 주문: {found.name}, {found.symbol}, {found.get_completion_percent()}")
    assert found is not None, "조회 실패"
    assert found.name == "bot1", "조회된 주문이 잘못되었습니다"
    print("✅ name으로 조회 성공")

    # 전체 조회
    print("\n[전체 조회]")
    all_orders = repo.find_all()
    print(f"전체 주문 개수: {len(all_orders)}")
    for o in all_orders:
        print(f"  - {o.name}: {o.symbol}, {o.order_type.value}, {o.get_completion_percent()}")
    assert len(all_orders) >= 2, "전체 조회 실패"
    print("✅ 전체 조회 성공")

    # 업데이트
    print("\n[주문 업데이트]")
    order1.trade_count = 2
    order1.add_trade_result({"amount": 10, "price": 51.0, "total": 510.0})
    repo.save(order1)
    updated = repo.find_by_name("bot1")
    print(f"업데이트된 주문: {updated.trade_count}/{updated.total_count}")
    assert updated.trade_count == 2, "업데이트 실패"
    assert len(updated.trade_result_list) == 2, "거래 결과 리스트 업데이트 실패"
    print("✅ 주문 업데이트 성공")

    session.close()
    print("\n✅ Order Repository 테스트 완료\n")


def test_sell_order_today():
    """오늘 매도 주문 확인 테스트"""
    print("=" * 60)
    print("오늘 매도 주문 확인 테스트")
    print("=" * 60)

    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyOrderRepository(session)

    # 매도 주문 생성
    print("\n[매도 주문 생성]")
    sell_order = Order(
        name="sell_bot",
        date_added=datetime.now(),
        symbol="LABU",
        trade_result_list=[],
        order_type=OrderType.SELL_1_4,
        trade_count=0,
        total_count=4,
        remain_value=1000.0,
        total_value=1000.0
    )
    repo.save(sell_order)
    print("✅ 매도 주문 생성 완료")

    # 오늘 매도 주문 확인
    print("\n[오늘 매도 주문 확인]")
    has_sell = repo.has_sell_order_today("sell_bot")
    print(f"sell_bot의 오늘 매도 주문 존재: {has_sell}")
    assert has_sell == True, "매도 주문 확인 실패"

    has_sell_none = repo.has_sell_order_today("nonexistent_bot")
    print(f"nonexistent_bot의 오늘 매도 주문 존재: {has_sell_none}")
    assert has_sell_none == False, "존재하지 않는 봇의 매도 주문 확인 실패"

    # 매수 주문은 False여야 함
    buy_order = Order(
        name="buy_bot",
        date_added=datetime.now(),
        symbol="SOXL",
        trade_result_list=[],
        order_type=OrderType.BUY,
        trade_count=0,
        total_count=3,
        remain_value=500.0,
        total_value=500.0
    )
    repo.save(buy_order)
    has_sell_buy = repo.has_sell_order_today("buy_bot")
    print(f"buy_bot의 오늘 매도 주문 존재 (매수 주문): {has_sell_buy}")
    assert has_sell_buy == False, "매수 주문이 매도로 인식됨"

    session.close()
    print("\n✅ 오늘 매도 주문 확인 테스트 완료\n")


def test_delete_operations():
    """삭제 테스트"""
    print("=" * 60)
    print("삭제 테스트")
    print("=" * 60)

    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyOrderRepository(session)

    # 테스트용 주문 생성
    print("\n[테스트용 주문 생성]")
    test_order = Order(
        name="test_order",
        date_added=datetime.now(),
        symbol="TEST",
        trade_result_list=[{"test": "data"}],
        order_type=OrderType.BUY,
        trade_count=0,
        total_count=1,
        remain_value=100.0,
        total_value=100.0
    )
    repo.save(test_order)
    print("✅ 테스트 주문 생성 완료")

    # name으로 삭제
    print("\n[name으로 삭제]")
    repo.delete_by_name("test_order")
    found = repo.find_by_name("test_order")
    assert found is None, "삭제 실패"
    print("✅ name으로 삭제 성공")

    # 오래된 주문 삭제
    print("\n[오래된 주문 삭제]")
    old_order = Order(
        name="old_order",
        date_added=datetime.now() - timedelta(days=2),
        symbol="OLD",
        trade_result_list=[],
        order_type=OrderType.BUY,
        trade_count=0,
        total_count=1,
        remain_value=100.0,
        total_value=100.0
    )
    repo.save(old_order)

    today = date.today()
    deleted_count = repo.delete_old_orders(today)
    print(f"삭제된 오래된 주문 개수: {deleted_count}")
    assert deleted_count >= 1, "오래된 주문 삭제 실패"

    session.close()
    print("\n✅ 삭제 테스트 완료\n")


if __name__ == "__main__":
    test_order_creation()
    test_order_repository()
    test_sell_order_today()
    test_delete_operations()

    print("=" * 60)
    print("✅ 모든 Order 테스트 통과!")
    print("=" * 60)
