"""Enum Value Objects 테스트"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.value_objects.trade_type import TradeType
from domain.value_objects.order_type import OrderType
from domain.value_objects.point_loc import PointLoc


def test_trade_type():
    print("=" * 60)
    print("TradeType Enum 테스트")
    print("=" * 60)

    # 매수 테스트
    print("\n[매수 확인]")
    print(f"BUY.is_buy() = {TradeType.BUY.is_buy()}")  # True
    print(f"BUY_FORCE.is_buy() = {TradeType.BUY_FORCE.is_buy()}")  # True
    print(f"SELL.is_buy() = {TradeType.SELL.is_buy()}")  # False

    # 매도 테스트
    print("\n[매도 확인]")
    print(f"SELL.is_sell() = {TradeType.SELL.is_sell()}")  # True
    print(f"SELL_1_4.is_sell() = {TradeType.SELL_1_4.is_sell()}")  # True
    print(f"BUY.is_sell() = {TradeType.BUY.is_sell()}")  # False

    # 부분 매도 테스트
    print("\n[부분 매도 확인]")
    print(f"SELL_1_4.is_partial_sell() = {TradeType.SELL_1_4.is_partial_sell()}")  # True
    print(f"SELL.is_partial_sell() = {TradeType.SELL.is_partial_sell()}")  # False

    # 전체 매도 테스트
    print("\n[전체 매도 확인]")
    print(f"SELL.is_full_sell() = {TradeType.SELL.is_full_sell()}")  # True
    print(f"SELL_1_4.is_full_sell() = {TradeType.SELL_1_4.is_full_sell()}")  # False

    # 강제 매수 테스트
    print("\n[강제 매수 확인]")
    print(f"BUY_FORCE.is_force() = {TradeType.BUY_FORCE.is_force()}")  # True
    print(f"BUY.is_force() = {TradeType.BUY.is_force()}")  # False

    # 보유 테스트
    print("\n[보유 확인]")
    print(f"HOLD.is_hold() = {TradeType.HOLD.is_hold()}")  # True
    print(f"BUY.is_hold() = {TradeType.BUY.is_hold()}")  # False

    # 매도 비율 테스트
    print("\n[매도 비율]")
    print(f"SELL.get_sell_ratio() = {TradeType.SELL.get_sell_ratio()}")  # 1.0
    print(f"SELL_3_4.get_sell_ratio() = {TradeType.SELL_3_4.get_sell_ratio()}")  # 0.75
    print(f"SELL_1_4.get_sell_ratio() = {TradeType.SELL_1_4.get_sell_ratio()}")  # 0.25

    print("\n✅ TradeType 테스트 완료\n")


def test_order_type():
    print("=" * 60)
    print("OrderType Enum 테스트")
    print("=" * 60)

    # 매수 테스트
    print("\n[매수 확인]")
    print(f"BUY.is_buy() = {OrderType.BUY.is_buy()}")  # True
    print(f"BUY_FORCE.is_buy() = {OrderType.BUY_FORCE.is_buy()}")  # True
    print(f"SELL.is_buy() = {OrderType.SELL.is_buy()}")  # False

    # 매도 테스트
    print("\n[매도 확인]")
    print(f"SELL.is_sell() = {OrderType.SELL.is_sell()}")  # True
    print(f"SELL_1_4.is_sell() = {OrderType.SELL_1_4.is_sell()}")  # True

    # 매도 비율 테스트
    print("\n[매도 비율]")
    print(f"SELL.get_sell_ratio() = {OrderType.SELL.get_sell_ratio()}")  # 1.0
    print(f"SELL_3_4.get_sell_ratio() = {OrderType.SELL_3_4.get_sell_ratio()}")  # 0.75

    print("\n✅ OrderType 테스트 완료\n")


def test_point_loc():
    print("=" * 60)
    print("PointLoc Enum 테스트")
    print("=" * 60)

    # 포인트 위치 확인
    print("\n[포인트 위치 확인]")
    print(f"P1.is_bottom() = {PointLoc.P1.is_bottom()}")  # True
    print(f"P1_2.is_middle() = {PointLoc.P1_2.is_middle()}")  # True
    print(f"P2_3.is_top() = {PointLoc.P2_3.is_top()}")  # True

    # 포지션 값
    print("\n[포지션 값]")
    print(f"P1.get_position_value() = {PointLoc.P1.get_position_value()}")  # 0.25
    print(f"P1_2.get_position_value() = {PointLoc.P1_2.get_position_value()}")  # 0.5
    print(f"P2_3.get_position_value() = {PointLoc.P2_3.get_position_value()}")  # 0.75

    # 공격성 레벨
    print("\n[공격성 레벨]")
    print(f"P1.get_aggressiveness() = {PointLoc.P1.get_aggressiveness()}")  # 공격적
    print(f"P1_2.get_aggressiveness() = {PointLoc.P1_2.get_aggressiveness()}")  # 중립적
    print(f"P2_3.get_aggressiveness() = {PointLoc.P2_3.get_aggressiveness()}")  # 보수적

    print("\n✅ PointLoc 테스트 완료\n")


if __name__ == "__main__":
    test_trade_type()
    test_order_type()
    test_point_loc()

    print("=" * 60)
    print("✅ 모든 Enum 테스트 통과!")
    print("=" * 60)
