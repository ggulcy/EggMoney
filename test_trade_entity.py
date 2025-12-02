"""Trade Entity 테스트"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.trade import Trade
from domain.value_objects.trade_type import TradeType


def test_trade_creation():
    """Trade 생성 및 검증 테스트"""
    print("=" * 60)
    print("Trade 생성 및 검증 테스트")
    print("=" * 60)

    # 정상 생성
    print("\n[정상 생성]")
    trade = Trade(
        name="bot1",
        symbol="SOXL",
        purchase_price=50.0,
        amount=10.0,
        trade_type=TradeType.BUY,
        total_price=500.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )
    print(f"✅ Trade 생성 성공: {trade}")

    # 검증 실패 테스트
    print("\n[검증 실패 테스트]")
    try:
        invalid_trade = Trade(
            name="",  # 빈 이름
            symbol="SOXL",
            purchase_price=50.0,
            amount=10.0,
            trade_type=TradeType.BUY,
            total_price=500.0,
            date_added=datetime.now(),
            latest_date_trade=datetime.now()
        )
        print("❌ 검증 실패: 빈 이름이 허용되었습니다")
    except ValueError as e:
        print(f"✅ 검증 성공: {e}")

    try:
        invalid_trade = Trade(
            name="bot1",
            symbol="SOXL",
            purchase_price=-50.0,  # 음수 가격
            amount=10.0,
            trade_type=TradeType.BUY,
            total_price=500.0,
            date_added=datetime.now(),
            latest_date_trade=datetime.now()
        )
        print("❌ 검증 실패: 음수 가격이 허용되었습니다")
    except ValueError as e:
        print(f"✅ 검증 성공: {e}")

    print("\n✅ Trade 생성 및 검증 테스트 완료\n")


def test_average_price():
    """평균 단가 계산 테스트"""
    print("=" * 60)
    print("평균 단가 계산 테스트")
    print("=" * 60)

    trade = Trade(
        name="bot1",
        symbol="SOXL",
        purchase_price=50.0,
        amount=10.0,
        trade_type=TradeType.BUY,
        total_price=500.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )

    avg_price = trade.get_average_price()
    print(f"\n총액: ${trade.total_price:,.2f}")
    print(f"수량: {trade.amount}")
    print(f"평균 단가: ${avg_price:,.2f}")
    assert avg_price == 50.0, "평균 단가 계산 오류"
    print("✅ 평균 단가 계산 정확함")

    # 수량이 0일 때
    trade.amount = 0.0
    avg_price = trade.get_average_price()
    print(f"\n수량 0일 때 평균 단가: ${avg_price:,.2f}")
    assert avg_price == 0.0, "수량 0일 때 평균 단가는 0이어야 함"
    print("✅ 수량 0일 때 평균 단가 계산 정확함")

    print("\n✅ 평균 단가 계산 테스트 완료\n")


def test_rebalance_buy():
    """매수 리밸런싱 테스트"""
    print("=" * 60)
    print("매수 리밸런싱 테스트")
    print("=" * 60)

    # 초기 거래: 10주 @ $50 = $500
    trade = Trade(
        name="bot1",
        symbol="SOXL",
        purchase_price=50.0,
        amount=10.0,
        trade_type=TradeType.BUY,
        total_price=500.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )

    print(f"\n[초기 상태]")
    print(f"수량: {trade.amount}")
    print(f"평균 단가: ${trade.purchase_price:,.2f}")
    print(f"총액: ${trade.total_price:,.2f}")

    # 추가 매수: 5주 @ $60 = $300
    print(f"\n[추가 매수: 5주 @ $60 = $300]")
    trade.rebalance_buy(
        buy_amount=5.0,
        buy_unit_price=60.0,
        buy_total_price=300.0
    )

    print(f"수량: {trade.amount}")  # 15
    print(f"평균 단가: ${trade.purchase_price:,.2f}")  # 53.33 (800/15)
    print(f"총액: ${trade.total_price:,.2f}")  # 800

    assert trade.amount == 15.0, "수량이 잘못되었습니다"
    assert trade.total_price == 800.0, "총액이 잘못되었습니다"
    assert abs(trade.purchase_price - 53.33) < 0.01, "평균 단가가 잘못되었습니다"
    print("✅ 매수 리밸런싱 정확함")

    # 추가 매수: 10주 @ $40 = $400
    print(f"\n[추가 매수: 10주 @ $40 = $400]")
    trade.rebalance_buy(
        buy_amount=10.0,
        buy_unit_price=40.0,
        buy_total_price=400.0
    )

    print(f"수량: {trade.amount}")  # 25
    print(f"평균 단가: ${trade.purchase_price:,.2f}")  # 48.0 (1200/25)
    print(f"총액: ${trade.total_price:,.2f}")  # 1200

    assert trade.amount == 25.0, "수량이 잘못되었습니다"
    assert trade.total_price == 1200.0, "총액이 잘못되었습니다"
    assert trade.purchase_price == 48.0, "평균 단가가 잘못되었습니다"
    print("✅ 2차 매수 리밸런싱 정확함")

    print("\n✅ 매수 리밸런싱 테스트 완료\n")


def test_rebalance_sell():
    """매도 리밸런싱 테스트"""
    print("=" * 60)
    print("매도 리밸런싱 테스트")
    print("=" * 60)

    # 초기 거래: 20주 @ $50 = $1000
    trade = Trade(
        name="bot1",
        symbol="SOXL",
        purchase_price=50.0,
        amount=20.0,
        trade_type=TradeType.BUY,
        total_price=1000.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )

    print(f"\n[초기 상태]")
    print(f"수량: {trade.amount}")
    print(f"평균 단가: ${trade.purchase_price:,.2f}")
    print(f"총액: ${trade.total_price:,.2f}")

    # 부분 매도: 5주
    print(f"\n[부분 매도: 5주]")
    trade.rebalance_sell(sell_amount=5.0)

    print(f"수량: {trade.amount}")  # 15
    print(f"평균 단가: ${trade.purchase_price:,.2f}")  # 50 (변동 없음)
    print(f"총액: ${trade.total_price:,.2f}")  # 750 (15 * 50)

    assert trade.amount == 15.0, "수량이 잘못되었습니다"
    assert trade.purchase_price == 50.0, "평균 단가는 유지되어야 합니다"
    assert trade.total_price == 750.0, "총액이 잘못되었습니다"
    print("✅ 부분 매도 리밸런싱 정확함")

    # 전체 매도: 15주
    print(f"\n[전체 매도: 15주]")
    trade.rebalance_sell(sell_amount=15.0)

    print(f"수량: {trade.amount}")  # 0
    print(f"평균 단가: ${trade.purchase_price:,.2f}")  # 50 (변동 없음)
    print(f"총액: ${trade.total_price:,.2f}")  # 0

    assert trade.amount == 0.0, "수량이 잘못되었습니다"
    assert trade.total_price == 0.0, "총액이 잘못되었습니다"
    print("✅ 전체 매도 리밸런싱 정확함")

    # 초과 매도 테스트
    print(f"\n[초과 매도 테스트]")
    try:
        trade.rebalance_sell(sell_amount=10.0)  # 보유 수량 0인데 매도 시도
        print("❌ 초과 매도가 허용되었습니다")
    except ValueError as e:
        print(f"✅ 초과 매도 방지: {e}")

    print("\n✅ 매도 리밸런싱 테스트 완료\n")


def test_is_active():
    """활성 거래 확인 테스트"""
    print("=" * 60)
    print("활성 거래 확인 테스트")
    print("=" * 60)

    # 활성 거래 (amount > 0)
    trade = Trade(
        name="bot1",
        symbol="SOXL",
        purchase_price=50.0,
        amount=10.0,
        trade_type=TradeType.BUY,
        total_price=500.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )

    print(f"\n수량: {trade.amount}")
    print(f"활성 거래: {trade.is_active()}")
    assert trade.is_active() == True, "활성 거래로 판단되어야 합니다"
    print("✅ 활성 거래 확인 정확함")

    # 비활성 거래 (amount = 0)
    trade.amount = 0.0
    print(f"\n수량: {trade.amount}")
    print(f"활성 거래: {trade.is_active()}")
    assert trade.is_active() == False, "비활성 거래로 판단되어야 합니다"
    print("✅ 비활성 거래 확인 정확함")

    print("\n✅ 활성 거래 확인 테스트 완료\n")


def test_complex_scenario():
    """복합 시나리오 테스트"""
    print("=" * 60)
    print("복합 시나리오 테스트 (DCA 전략)")
    print("=" * 60)

    # 1차 매수: 10주 @ $100 = $1000
    print("\n[1차 매수: 10주 @ $100]")
    trade = Trade(
        name="SOXL_bot",
        symbol="SOXL",
        purchase_price=100.0,
        amount=10.0,
        trade_type=TradeType.BUY,
        total_price=1000.0,
        date_added=datetime.now(),
        latest_date_trade=datetime.now()
    )
    print(f"수량: {trade.amount}, 평단: ${trade.purchase_price:,.2f}, 총액: ${trade.total_price:,.2f}")

    # 2차 매수 (하락 시): 15주 @ $80 = $1200
    print("\n[2차 매수: 15주 @ $80 (하락)]")
    trade.rebalance_buy(15.0, 80.0, 1200.0)
    print(f"수량: {trade.amount}, 평단: ${trade.purchase_price:,.2f}, 총액: ${trade.total_price:,.2f}")
    assert abs(trade.purchase_price - 88.0) < 0.01, "평단 계산 오류"  # 2200/25 = 88

    # 3차 매수 (추가 하락): 20주 @ $60 = $1200
    print("\n[3차 매수: 20주 @ $60 (추가 하락)]")
    trade.rebalance_buy(20.0, 60.0, 1200.0)
    print(f"수량: {trade.amount}, 평단: ${trade.purchase_price:,.2f}, 총액: ${trade.total_price:,.2f}")
    assert abs(trade.purchase_price - 75.56) < 0.01, "평단 계산 오류"  # 3400/45 = 75.56

    # 1차 매도 (일부): 10주
    print("\n[1차 매도: 10주 (부분 익절)]")
    trade.rebalance_sell(10.0)
    print(f"수량: {trade.amount}, 평단: ${trade.purchase_price:,.2f}, 총액: ${trade.total_price:,.2f}")
    assert trade.amount == 35.0, "수량 계산 오류"
    assert abs(trade.purchase_price - 75.56) < 0.01, "평단 유지 오류"

    # 2차 매도 (나머지): 35주
    print("\n[2차 매도: 35주 (전체 청산)]")
    trade.rebalance_sell(35.0)
    print(f"수량: {trade.amount}, 평단: ${trade.purchase_price:,.2f}, 총액: ${trade.total_price:,.2f}")
    assert trade.amount == 0.0, "수량이 0이어야 합니다"
    assert not trade.is_active(), "비활성 상태여야 합니다"

    print("\n✅ 복합 시나리오 테스트 완료\n")


if __name__ == "__main__":
    test_trade_creation()
    test_average_price()
    test_rebalance_buy()
    test_rebalance_sell()
    test_is_active()
    test_complex_scenario()

    print("=" * 60)
    print("✅ 모든 Trade Entity 테스트 통과!")
    print("=" * 60)
