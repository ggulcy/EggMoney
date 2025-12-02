"""Config Layer (util, key_store) 테스트"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import util, key_store
from config.item import BotAdmin, admin
from domain.value_objects.point_loc import PointLoc


def test_weekday_conversion():
    """요일 변환 테스트"""
    print("=" * 60)
    print("요일 변환 테스트")
    print("=" * 60)

    # 문자열 → 리스트
    print("\n[문자열 → 리스트]")
    weekday_str = "월, 수, 금"
    weekday_list = util.weekday_str_to_list(weekday_str)
    print(f"{weekday_str} → {weekday_list}")
    assert weekday_list == [0, 2, 4], "요일 변환 실패"

    # 리스트 → 문자열
    print("\n[리스트 → 문자열]")
    result_str = util.weekday_list_to_str(weekday_list)
    print(f"{weekday_list} → {result_str}")
    assert result_str == weekday_str, "요일 역변환 실패"

    print("\n✅ 요일 변환 테스트 완료\n")


def test_time_utilities():
    """시간 유틸리티 테스트"""
    print("=" * 60)
    print("시간 유틸리티 테스트")
    print("=" * 60)

    # 메시지 전송 시간
    print("\n[메시지 전송 시간 (서머타임 고려)]")
    msg_times = util.get_msg_times()
    print(f"메시지 전송 시간: {msg_times}")
    assert len(msg_times) == 2, "메시지 시간이 2개여야 함"

    # TWAP 시간
    print("\n[TWAP 시간 (서머타임 고려)]")
    twap_times = util.get_twap_times()
    print(f"TWAP 시간: {twap_times}")
    assert len(twap_times) == 2, "TWAP 시간이 2개여야 함"

    # 이전 날짜
    print("\n[이전 날짜 계산]")
    prev_date = util.get_previous_date(7)
    print(f"7일 전: {prev_date}")
    assert len(prev_date) == 8, "날짜 형식은 YYYYMMDD"

    # 시간 타임라인
    print("\n[시간 타임라인 생성]")
    timeline = util.get_time_timeline("01:00", "05:00", 5)
    print(f"타임라인: {timeline}")
    assert len(timeline) == 5, "타임라인이 5개여야 함"
    assert timeline[0] == "01:00", "시작 시간 확인"
    assert timeline[-1] == "05:00", "종료 시간 확인"

    print("\n✅ 시간 유틸리티 테스트 완료\n")


def test_trading_calculations():
    """거래 계산 테스트"""
    print("=" * 60)
    print("거래 계산 테스트")
    print("=" * 60)

    # 수익률 계산
    print("\n[수익률 계산]")
    profit_rate = util.get_profit_rate(110, 100)
    print(f"매수가: $100, 현재가: $110 → 수익률: {profit_rate}%")
    assert profit_rate == 10.0, "수익률 계산 오류"

    # 매수 수량 계산
    print("\n[매수 수량 계산]")
    buy_amount = util.get_buy_amount(1000, 50.5)
    print(f"시드: $1000, 가격: $50.5 → 수량: {buy_amount}")
    assert buy_amount == 19, "매수 수량 계산 오류"

    # 티어 계산
    print("\n[티어 계산]")
    t_value = util.get_T(3500, 1000)
    print(f"총액: $3500, 시드: $1000 → 티어: {t_value}")
    assert t_value == 3.5, "티어 계산 오류"

    # 손절 가격 계산 (P1 - 손절 없음)
    print("\n[손절 가격 계산 - P1]")
    point_loc_value = util.get_point_loc(20, 5, 3, PointLoc.P1)
    print(f"div=20%, max_tier=5, t=3, P1 → {point_loc_value}")
    assert point_loc_value > 0, "P1은 항상 양수"

    print("\n✅ 거래 계산 테스트 완료\n")


def test_formatting():
    """포맷팅 테스트"""
    print("=" * 60)
    print("포맷팅 테스트")
    print("=" * 60)

    # 진행 바
    print("\n[진행 바]")
    bar_30 = util.create_progress_bar(30)
    print(f"30%: {bar_30}")
    bar_70 = util.create_progress_bar(70)
    print(f"70%: {bar_70}")

    # OX 이모지
    print("\n[OX 이모지]")
    ox_true = util.get_ox_emoji(True)
    ox_false = util.get_ox_emoji(False)
    print(f"True: {ox_true}, False: {ox_false}")
    assert ox_true == "⭕️", "True는 ⭕️"
    assert ox_false == "❌", "False는 ❌"

    # PointLoc 텍스트
    print("\n[PointLoc 텍스트]")
    p1_text = util.get_point_loc_text(PointLoc.P1)
    p1_2_text = util.get_point_loc_text(PointLoc.P1_2)
    p2_3_text = util.get_point_loc_text(PointLoc.P2_3)
    print(f"P1: {p1_text}, P1_2: {p1_2_text}, P2_3: {p2_3_text}")
    assert p1_text == "손절없음", "P1 텍스트 확인"
    assert p1_2_text == "1/2지점", "P1_2 텍스트 확인"
    assert p2_3_text == "2/3지점", "P2_3 텍스트 확인"

    print("\n✅ 포맷팅 테스트 완료\n")


def test_key_store():
    """Key-Value Store 테스트"""
    print("=" * 60)
    print("Key-Value Store 테스트")
    print("=" * 60)

    # 쓰기
    print("\n[데이터 쓰기]")
    key_store.write("TEST_KEY", "test_value")
    print("TEST_KEY = 'test_value' 저장 완료")

    # 읽기
    print("\n[데이터 읽기]")
    value = key_store.read("TEST_KEY")
    print(f"TEST_KEY = {value}")
    assert value == "test_value", "저장된 값 확인"

    # 기본값 확인
    print("\n[기본값 확인]")
    trade_date = key_store.read(key_store.TRADE_DATE)
    print(f"TRADE_DATE (기본값): {trade_date}")
    assert trade_date == [1, 2, 3, 4, 5], "기본 거래일 확인"

    trade_time = key_store.read(key_store.TRADE_TIME)
    print(f"TRADE_TIME (기본값): {trade_time}")
    assert trade_time == "00:05", "기본 거래 시간 확인"

    twap_count = key_store.read(key_store.TWAP_COUNT)
    print(f"TWAP_COUNT (기본값): {twap_count}")
    assert twap_count == 3, "기본 TWAP 분할 수 확인"

    # 전체 키 출력
    print("\n[전체 키 출력]")
    key_store.print_all_keys()

    print("\n✅ Key-Value Store 테스트 완료\n")


def test_bot_name_check():
    """봇 이름 확인 테스트"""
    print("=" * 60)
    print("봇 이름 확인 테스트")
    print("=" * 60)

    print(f"\n현재 admin: {admin.value}")

    # 현재 admin 포함
    names_with_admin = ["chan", "choe"]
    result = util.check_bot_name(names_with_admin)
    print(f"{names_with_admin}에 {admin.value} 포함 여부: {result}")

    # 현재 admin 미포함
    names_without_admin = ["sk"]
    result = util.check_bot_name(names_without_admin)
    print(f"{names_without_admin}에 {admin.value} 포함 여부: {result}")

    print("\n✅ 봇 이름 확인 테스트 완료\n")


if __name__ == "__main__":
    test_weekday_conversion()
    test_time_utilities()
    test_trading_calculations()
    test_formatting()
    test_key_store()
    test_bot_name_check()

    print("=" * 60)
    print("✅ 모든 Config Layer 테스트 통과!")
    print("=" * 60)
