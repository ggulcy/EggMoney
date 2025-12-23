"""_merge_trade_results 함수 테스트 - TWAP 부분 체결 시나리오"""
import sys
import os
from datetime import datetime
from unittest.mock import Mock, MagicMock

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.order import Order
from domain.value_objects.order_type import OrderType
from domain.value_objects.trade_type import TradeType
from domain.value_objects.trade_result import TradeResult
from usecase.trading_usecase import TradingUsecase


def create_mock_trading_usecase() -> TradingUsecase:
    """Mock TradingUsecase 생성"""
    mock_bot_info_repo = Mock()
    mock_trade_repo = Mock()
    mock_history_repo = Mock()
    mock_order_repo = Mock()
    mock_exchange_repo = Mock()
    mock_message_repo = Mock()

    usecase = TradingUsecase(
        bot_info_repo=mock_bot_info_repo,
        trade_repo=mock_trade_repo,
        history_repo=mock_history_repo,
        order_repo=mock_order_repo,
        exchange_repo=mock_exchange_repo,
        message_repo=mock_message_repo
    )
    return usecase


def create_sell_order(total_value: int = 100) -> Order:
    """전체 매도(SELL) 주문서 생성"""
    return Order(
        name="Tesla",
        date_added=datetime.now(),
        symbol="TSLA",
        trade_result_list=[],
        order_type=OrderType.SELL,
        trade_count=5,
        total_count=5,
        remain_value=total_value,
        total_value=total_value
    )


def create_partial_sell_order(order_type: OrderType, total_value: int = 100) -> Order:
    """부분 매도 주문서 생성"""
    return Order(
        name="Tesla",
        date_added=datetime.now(),
        symbol="TSLA",
        trade_result_list=[],
        order_type=order_type,
        trade_count=5,
        total_count=5,
        remain_value=total_value,
        total_value=total_value
    )


def create_trade_result(amount: int, unit_price: float = 100.0) -> TradeResult:
    """TradeResult 생성"""
    return TradeResult(
        trade_type=TradeType.SELL,
        amount=amount,
        unit_price=unit_price,
        total_price=amount * unit_price
    )


class TestMergeTradeResultsFullSell:
    """전체 매도(SELL) 시나리오 테스트"""

    def test_full_sell_all_success(self):
        """
        시나리오: 전체 매도 - 5/5 모두 체결 성공
        예상: trade_type = SELL 유지
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 5회 모두 성공 (각 20주씩)
        trade_result_list = [
            create_trade_result(20),
            create_trade_result(20),
            create_trade_result(20),
            create_trade_result(20),
            create_trade_result(20),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL, f"Expected SELL, got {result.trade_type}"
        assert result.amount == 100
        # 텔레그램 메시지 호출 안됨
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_full_sell_all_success PASSED")

    def test_full_sell_partial_success_early_close(self):
        """
        시나리오: 전체 매도 - 1/5만 체결 (장 조기종료 등)
        예상: trade_type = SELL → SELL_PART 변경, 텔레그램 알림
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 1회만 성공 (20주), 나머지 4회 실패 (None 필터링됨)
        trade_result_list = [
            create_trade_result(20),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_PART, f"Expected SELL_PART, got {result.trade_type}"
        assert result.amount == 20
        # 텔레그램 메시지 호출됨
        usecase.message_repo.send_message.assert_called_once()
        call_args = usecase.message_repo.send_message.call_args[0][0]
        assert "TWAP 부분 체결" in call_args
        assert "원래 매도 수량: 100주" in call_args
        assert "실제 체결 수량: 20주" in call_args
        assert "미체결 수량: 80주" in call_args
        assert "SELL → SELL_PART" in call_args
        print("✅ test_full_sell_partial_success_early_close PASSED")

    def test_full_sell_3_of_5_success(self):
        """
        시나리오: 전체 매도 - 3/5 체결 (60%)
        예상: trade_type = SELL → SELL_PART 변경
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 3회 성공 (각 20주씩 = 60주)
        trade_result_list = [
            create_trade_result(20),
            create_trade_result(20),
            create_trade_result(20),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_PART
        assert result.amount == 60
        usecase.message_repo.send_message.assert_called_once()
        call_args = usecase.message_repo.send_message.call_args[0][0]
        assert "미체결 수량: 40주" in call_args
        print("✅ test_full_sell_3_of_5_success PASSED")

    def test_full_sell_99_of_100(self):
        """
        시나리오: 전체 매도 100주 중 99주만 체결 (경계 케이스)
        예상: trade_type = SELL → SELL_PART 변경 (1주라도 미체결이면)
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 99주 체결
        trade_result_list = [
            create_trade_result(99),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_PART
        assert result.amount == 99
        usecase.message_repo.send_message.assert_called_once()
        print("✅ test_full_sell_99_of_100 PASSED")

    def test_full_sell_no_success(self):
        """
        시나리오: 전체 매도 - 0/5 체결 (모두 실패)
        예상: None 반환 (trade_result_list가 비어있음)
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 모두 실패 (빈 리스트)
        trade_result_list = []

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is None
        print("✅ test_full_sell_no_success PASSED")


class TestMergeTradeResultsPartialSell:
    """부분 매도(SELL_1_4, SELL_3_4, SELL_PART) 시나리오 테스트"""

    def test_partial_sell_1_4_all_success(self):
        """
        시나리오: 1/4 부분 매도 - 모두 체결
        예상: trade_type = SELL_1_4 유지 (변경 없음)
        """
        usecase = create_mock_trading_usecase()
        order = create_partial_sell_order(OrderType.SELL_1_4, total_value=25)

        trade_result_list = [
            create_trade_result(5),
            create_trade_result(5),
            create_trade_result(5),
            create_trade_result(5),
            create_trade_result(5),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_1_4
        assert result.amount == 25
        # 부분 매도는 원래 리밸런싱이므로 타입 변경 알림 없음
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_partial_sell_1_4_all_success PASSED")

    def test_partial_sell_3_4_partial_success(self):
        """
        시나리오: 3/4 부분 매도 - 일부만 체결
        예상: trade_type = SELL_3_4 유지 (이미 부분 매도이므로 변경 없음)
        """
        usecase = create_mock_trading_usecase()
        order = create_partial_sell_order(OrderType.SELL_3_4, total_value=75)

        # 절반만 체결
        trade_result_list = [
            create_trade_result(20),
            create_trade_result(20),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_3_4  # 변경 없음
        assert result.amount == 40
        # 부분 매도는 타입 변경 로직 적용 안됨 (SELL만 해당)
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_partial_sell_3_4_partial_success PASSED")

    def test_partial_sell_part_partial_success(self):
        """
        시나리오: SELL_PART - 일부만 체결
        예상: trade_type = SELL_PART 유지
        """
        usecase = create_mock_trading_usecase()
        order = create_partial_sell_order(OrderType.SELL_PART, total_value=50)

        trade_result_list = [
            create_trade_result(10),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.SELL_PART
        assert result.amount == 10
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_partial_sell_part_partial_success PASSED")


class TestMergeTradeResultsBuy:
    """매수(BUY) 시나리오 테스트 - 타입 변경 로직 영향 없음 확인"""

    def test_buy_all_success(self):
        """
        시나리오: 매수 - 모두 체결
        예상: trade_type = BUY 유지
        """
        usecase = create_mock_trading_usecase()
        order = Order(
            name="Tesla",
            date_added=datetime.now(),
            symbol="TSLA",
            trade_result_list=[],
            order_type=OrderType.BUY,
            trade_count=5,
            total_count=5,
            remain_value=1000,
            total_value=1000
        )

        trade_result_list = [
            TradeResult(TradeType.BUY, 10, 100.0, 1000.0),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.BUY
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_buy_all_success PASSED")

    def test_buy_partial_success(self):
        """
        시나리오: 매수 - 일부만 체결
        예상: trade_type = BUY 유지 (매수는 리밸런싱만 하므로 문제 없음)
        """
        usecase = create_mock_trading_usecase()
        order = Order(
            name="Tesla",
            date_added=datetime.now(),
            symbol="TSLA",
            trade_result_list=[],
            order_type=OrderType.BUY,
            trade_count=5,
            total_count=5,
            remain_value=1000,
            total_value=1000
        )

        # 일부만 체결
        trade_result_list = [
            TradeResult(TradeType.BUY, 2, 100.0, 200.0),
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.trade_type == TradeType.BUY  # 매수는 변경 없음
        usecase.message_repo.send_message.assert_not_called()
        print("✅ test_buy_partial_success PASSED")


class TestMergeTradeResultsEdgeCases:
    """경계 케이스 테스트"""

    def test_merge_calculates_correct_average_price(self):
        """
        시나리오: 여러 체결의 평균 단가 계산
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)

        # 다른 가격에 체결
        trade_result_list = [
            TradeResult(TradeType.SELL, 20, 100.0, 2000.0),  # 20주 × $100
            TradeResult(TradeType.SELL, 30, 110.0, 3300.0),  # 30주 × $110
            TradeResult(TradeType.SELL, 50, 105.0, 5250.0),  # 50주 × $105
        ]

        result = usecase._merge_trade_results(trade_result_list, order)

        assert result is not None
        assert result.amount == 100
        assert result.total_price == 10550.0
        # 평균 단가 = 10550 / 100 = 105.5
        assert result.unit_price == 105.5
        # 전량 체결이므로 SELL 유지
        assert result.trade_type == TradeType.SELL
        print("✅ test_merge_calculates_correct_average_price PASSED")

    def test_message_contains_correct_info(self):
        """
        시나리오: 텔레그램 메시지에 올바른 정보 포함 확인
        """
        usecase = create_mock_trading_usecase()
        order = create_sell_order(total_value=100)
        order.name = "MyBot"

        trade_result_list = [
            create_trade_result(35),  # 35주만 체결
        ]

        usecase._merge_trade_results(trade_result_list, order)

        call_args = usecase.message_repo.send_message.call_args[0][0]
        assert "[MyBot]" in call_args
        assert "원래 매도 수량: 100주" in call_args
        assert "실제 체결 수량: 35주" in call_args
        assert "미체결 수량: 65주" in call_args
        assert "Trade 유지" in call_args
        print("✅ test_message_contains_correct_info PASSED")


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("_merge_trade_results 함수 테스트")
    print("=" * 60 + "\n")

    # 전체 매도 테스트
    print("📌 전체 매도(SELL) 시나리오")
    print("-" * 40)
    test_full_sell = TestMergeTradeResultsFullSell()
    test_full_sell.test_full_sell_all_success()
    test_full_sell.test_full_sell_partial_success_early_close()
    test_full_sell.test_full_sell_3_of_5_success()
    test_full_sell.test_full_sell_99_of_100()
    test_full_sell.test_full_sell_no_success()

    print()

    # 부분 매도 테스트
    print("📌 부분 매도(SELL_1_4, SELL_3_4, SELL_PART) 시나리오")
    print("-" * 40)
    test_partial_sell = TestMergeTradeResultsPartialSell()
    test_partial_sell.test_partial_sell_1_4_all_success()
    test_partial_sell.test_partial_sell_3_4_partial_success()
    test_partial_sell.test_partial_sell_part_partial_success()

    print()

    # 매수 테스트
    print("📌 매수(BUY) 시나리오")
    print("-" * 40)
    test_buy = TestMergeTradeResultsBuy()
    test_buy.test_buy_all_success()
    test_buy.test_buy_partial_success()

    print()

    # 경계 케이스 테스트
    print("📌 경계 케이스")
    print("-" * 40)
    test_edge = TestMergeTradeResultsEdgeCases()
    test_edge.test_merge_calculates_correct_average_price()
    test_edge.test_message_contains_correct_info()

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_tests()
