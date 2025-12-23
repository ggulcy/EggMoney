"""장부거래(Netting) 기능 테스트"""
import sys
import os
from datetime import datetime
from unittest.mock import Mock, MagicMock

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.order import Order
from domain.value_objects.order_type import OrderType
from domain.value_objects.netting_pair import NettingPair
from usecase.order_usecase import OrderUsecase


class TestNettingPair:
    """NettingPair Value Object 테스트"""

    def test_create_netting_pair(self):
        """기본 생성 테스트"""
        buy_order = Order(
            name="bot1",
            date_added=datetime.now(),
            symbol="TQQQ",
            trade_result_list=[],
            order_type=OrderType.BUY,
            trade_count=5,
            total_count=5,
            remain_value=3000.0,  # $3000
            total_value=3000.0
        )
        sell_order = Order(
            name="bot2",
            date_added=datetime.now(),
            symbol="TQQQ",
            trade_result_list=[],
            order_type=OrderType.SELL,
            trade_count=5,
            total_count=5,
            remain_value=50,  # 50개
            total_value=50
        )

        pair = NettingPair(
            buy_order=buy_order,
            sell_order=sell_order,
            netting_amount=30,
            current_price=100.0
        )

        assert pair.symbol == "TQQQ"
        assert pair.netting_amount == 30
        assert pair.current_price == 100.0
        assert pair.total_value == 3000.0  # 30 * 100
        print("✅ test_create_netting_pair PASSED")

    def test_netting_pair_validation(self):
        """유효성 검증 테스트"""
        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        sell_order = Order(
            name="bot2", date_added=datetime.now(), symbol="SOXL",  # 다른 symbol
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )

        try:
            NettingPair(buy_order, sell_order, 30, 100.0)
            assert False, "Should raise ValueError for different symbols"
        except ValueError as e:
            assert "same symbol" in str(e)
            print("✅ test_netting_pair_validation PASSED (symbol mismatch detected)")

    def test_netting_pair_invalid_amount(self):
        """잘못된 수량 테스트"""
        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        sell_order = Order(
            name="bot2", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )

        try:
            NettingPair(buy_order, sell_order, 0, 100.0)  # 0개 상쇄
            assert False, "Should raise ValueError for zero amount"
        except ValueError as e:
            assert "positive" in str(e)
            print("✅ test_netting_pair_invalid_amount PASSED")


class TestOrderUsecaseNetting:
    """OrderUsecase의 Netting 메서드 테스트"""

    def setup_mocks(self):
        """Mock 객체 설정"""
        self.bot_info_repo = Mock()
        self.trade_repo = Mock()
        self.history_repo = Mock()
        self.order_repo = Mock()
        self.exchange_repo = Mock()

        self.usecase = OrderUsecase(
            bot_info_repo=self.bot_info_repo,
            trade_repo=self.trade_repo,
            history_repo=self.history_repo,
            order_repo=self.order_repo,
            exchange_repo=self.exchange_repo
        )

    def test_find_netting_orders_no_orders(self):
        """주문서가 없을 때"""
        self.setup_mocks()
        self.order_repo.find_all.return_value = []

        result = self.usecase.find_netting_orders()

        assert result == []
        print("✅ test_find_netting_orders_no_orders PASSED")

    def test_find_netting_orders_only_buy(self):
        """매수 주문서만 있을 때 (상쇄 불가)"""
        self.setup_mocks()

        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        self.order_repo.find_all.return_value = [buy_order]

        result = self.usecase.find_netting_orders()

        assert result == []
        print("✅ test_find_netting_orders_only_buy PASSED")

    def test_find_netting_orders_simple_pair(self):
        """단순 1:1 상쇄 테스트"""
        self.setup_mocks()

        # bot1: TQQQ 매수 $3000 (현재가 $100 → 30개)
        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        # bot2: TQQQ 매도 50개
        sell_order = Order(
            name="bot2", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )

        self.order_repo.find_all.return_value = [buy_order, sell_order]
        self.exchange_repo.get_price.return_value = 100.0  # 현재가 $100

        result = self.usecase.find_netting_orders()

        assert len(result) == 1
        pair = result[0]
        assert pair.buy_order.name == "bot1"
        assert pair.sell_order.name == "bot2"
        assert pair.netting_amount == 30  # min(30, 50) = 30
        assert pair.current_price == 100.0
        print("✅ test_find_netting_orders_simple_pair PASSED")
        print(f"   상쇄 결과: {pair}")

    def test_find_netting_orders_multiple_pairs(self):
        """
        다중 쌍 상쇄 테스트 (Greedy)

        입력:
        - A: TQQQ 매수 $3000 (30개)
        - B: TQQQ 매수 $2000 (20개)
        - C: TQQQ 매도 50개
        - D: TQQQ 매도 10개

        기대:
        1차: (A:30, C:50) → 30개 상쇄 → C 잔여 20개
        2차: (B:20, C:20) → 20개 상쇄 → C 잔여 0개
        D: 매칭 대상 없음
        """
        self.setup_mocks()

        order_a = Order(
            name="A", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        order_b = Order(
            name="B", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=2000, total_value=2000
        )
        order_c = Order(
            name="C", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )
        order_d = Order(
            name="D", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=10, total_value=10
        )

        self.order_repo.find_all.return_value = [order_a, order_b, order_c, order_d]
        self.exchange_repo.get_price.return_value = 100.0

        result = self.usecase.find_netting_orders()

        # 2개 쌍이 생성되어야 함
        assert len(result) == 2

        # 1차: A-C 30개 상쇄
        pair1 = result[0]
        assert pair1.buy_order.name == "A"
        assert pair1.sell_order.name == "C"
        assert pair1.netting_amount == 30

        # 2차: B-C 20개 상쇄
        pair2 = result[1]
        assert pair2.buy_order.name == "B"
        assert pair2.sell_order.name == "C"
        assert pair2.netting_amount == 20

        print("✅ test_find_netting_orders_multiple_pairs PASSED")
        print(f"   1차 상쇄: {pair1}")
        print(f"   2차 상쇄: {pair2}")
        print(f"   D(10개)는 매칭 대상 없음 → 실제 거래 예정")

    def test_find_netting_orders_different_symbols(self):
        """다른 symbol은 상쇄 안됨"""
        self.setup_mocks()

        buy_tqqq = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )
        sell_soxl = Order(
            name="bot2", date_added=datetime.now(), symbol="SOXL",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )

        self.order_repo.find_all.return_value = [buy_tqqq, sell_soxl]
        self.exchange_repo.get_price.return_value = 100.0

        result = self.usecase.find_netting_orders()

        assert result == []
        print("✅ test_find_netting_orders_different_symbols PASSED")

    def test_get_buy_amount_from_seed(self):
        """매수 금액 → 수량 변환 테스트"""
        self.setup_mocks()

        # $3000 / $100 = 30개
        result = self.usecase._get_buy_amount_from_seed(3000, 100)
        assert result == 30

        # $2500 / $100 = 25개 (소수점 버림)
        result = self.usecase._get_buy_amount_from_seed(2500, 100)
        assert result == 25

        # 현재가 0일 때
        result = self.usecase._get_buy_amount_from_seed(3000, 0)
        assert result == 0

        print("✅ test_get_buy_amount_from_seed PASSED")

    def test_update_order_after_netting_buy(self):
        """매수 주문서 업데이트 테스트"""
        self.setup_mocks()

        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=3000, total_value=3000
        )

        # 30개 상쇄 (현재가 $100 → $3000 차감)
        self.usecase.update_order_after_netting(buy_order, 30, 100.0)

        # 전량 상쇄 → 삭제 호출
        self.order_repo.delete_by_name.assert_called_once_with("bot1")
        print("✅ test_update_order_after_netting_buy PASSED (전량 상쇄 → 삭제)")

    def test_update_order_after_netting_buy_partial(self):
        """매수 주문서 부분 상쇄 테스트"""
        self.setup_mocks()

        buy_order = Order(
            name="bot1", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.BUY,
            trade_count=5, total_count=5, remain_value=5000, total_value=5000
        )

        # 30개 상쇄 (현재가 $100 → $3000 차감, 남은 $2000)
        self.usecase.update_order_after_netting(buy_order, 30, 100.0)

        assert buy_order.remain_value == 2000.0
        self.order_repo.save.assert_called_once()
        print("✅ test_update_order_after_netting_buy_partial PASSED (부분 상쇄 → 저장)")

    def test_update_order_after_netting_sell(self):
        """매도 주문서 업데이트 테스트"""
        self.setup_mocks()

        sell_order = Order(
            name="bot2", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=50, total_value=50
        )

        # 30개 상쇄 (남은 20개)
        self.usecase.update_order_after_netting(sell_order, 30, 100.0)

        assert sell_order.remain_value == 20
        self.order_repo.save.assert_called_once()
        print("✅ test_update_order_after_netting_sell PASSED (부분 상쇄 → 저장)")

    def test_update_order_after_netting_sell_full(self):
        """매도 주문서 전량 상쇄 테스트"""
        self.setup_mocks()

        sell_order = Order(
            name="bot2", date_added=datetime.now(), symbol="TQQQ",
            trade_result_list=[], order_type=OrderType.SELL,
            trade_count=5, total_count=5, remain_value=30, total_value=30
        )

        # 30개 상쇄 (전량)
        self.usecase.update_order_after_netting(sell_order, 30, 100.0)

        self.order_repo.delete_by_name.assert_called_once_with("bot2")
        print("✅ test_update_order_after_netting_sell_full PASSED (전량 상쇄 → 삭제)")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("장부거래(Netting) 기능 테스트 시작")
    print("=" * 60)

    # NettingPair 테스트
    print("\n[NettingPair Value Object 테스트]")
    netting_pair_tests = TestNettingPair()
    netting_pair_tests.test_create_netting_pair()
    netting_pair_tests.test_netting_pair_validation()
    netting_pair_tests.test_netting_pair_invalid_amount()

    # OrderUsecase Netting 테스트
    print("\n[OrderUsecase Netting 메서드 테스트]")
    usecase_tests = TestOrderUsecaseNetting()
    usecase_tests.test_find_netting_orders_no_orders()
    usecase_tests.test_find_netting_orders_only_buy()
    usecase_tests.test_find_netting_orders_simple_pair()
    usecase_tests.test_find_netting_orders_multiple_pairs()
    usecase_tests.test_find_netting_orders_different_symbols()
    usecase_tests.test_get_buy_amount_from_seed()
    usecase_tests.test_update_order_after_netting_buy()
    usecase_tests.test_update_order_after_netting_buy_partial()
    usecase_tests.test_update_order_after_netting_sell()
    usecase_tests.test_update_order_after_netting_sell_full()

    print("\n" + "=" * 60)
    print("모든 테스트 통과!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
