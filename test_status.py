"""Status Entity 및 Repository 테스트"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.status import Status
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories.status_repository_impl import SQLAlchemyStatusRepository


def test_status_creation():
    """Status 생성 및 검증 테스트"""
    print("=" * 60)
    print("Status 생성 및 검증 테스트")
    print("=" * 60)

    # 정상 생성
    print("\n[정상 생성]")
    status = Status(
        deposit_won=10000000,  # 1천만원
        deposit_dollar=5000,   # $5,000
        withdraw_won=2000000,  # 2백만원
        withdraw_dollar=1000   # $1,000
    )
    print(f"✅ Status 생성 성공: {status}")
    print(f"순 원화: ₩{status.get_net_won():,.0f}")
    print(f"순 달러: ${status.get_net_dollar():,.0f}")

    # 환율 적용 총액
    print("\n[환율 적용 총액 계산]")
    exchange_rate = 1300.0  # 1달러 = 1300원
    total_deposit = status.get_total_deposit(exchange_rate)
    total_withdraw = status.get_total_withdraw(exchange_rate)
    print(f"총 입금 (환율 {exchange_rate}원): ${total_deposit:,.2f}")
    print(f"총 출금 (환율 {exchange_rate}원): ${total_withdraw:,.2f}")

    # 검증 실패 테스트
    print("\n[검증 실패 테스트]")
    try:
        invalid_status = Status(
            deposit_won=-1000,  # 음수
            deposit_dollar=5000,
            withdraw_won=2000000,
            withdraw_dollar=1000
        )
        print("❌ 검증 실패: 음수 금액이 허용되었습니다")
    except ValueError as e:
        print(f"✅ 검증 성공: {e}")

    print("\n✅ Status 생성 및 검증 테스트 완료\n")


def test_status_repository():
    """Status Repository 테스트"""
    print("=" * 60)
    print("Status Repository 테스트")
    print("=" * 60)

    # SessionFactory 생성
    session_factory = SessionFactory()
    session = session_factory.create_session()
    repo = SQLAlchemyStatusRepository(session)

    # 초기 상태 확인
    print("\n[초기 상태 확인]")
    initial_status = repo.get_status()
    if initial_status:
        print(f"기존 상태 존재: {initial_status}")
    else:
        print("기존 상태 없음")

    # 새 상태 저장
    print("\n[새 상태 저장 (sync)]")
    new_status = Status(
        deposit_won=15000000,
        deposit_dollar=10000,
        withdraw_won=3000000,
        withdraw_dollar=2000
    )
    repo.sync_status(new_status)
    print("✅ 상태 저장 완료")

    # 저장된 상태 조회
    print("\n[저장된 상태 조회]")
    saved_status = repo.get_status()
    print(f"조회된 상태: {saved_status}")
    assert saved_status is not None, "조회 실패"
    assert saved_status.deposit_won == 15000000, "입금 원화 불일치"
    assert saved_status.deposit_dollar == 10000, "입금 달러 불일치"
    print("✅ 상태 조회 성공")

    # 상태 업데이트 (sync - 기존 데이터 삭제 후 재저장)
    print("\n[상태 업데이트]")
    updated_status = Status(
        deposit_won=20000000,
        deposit_dollar=15000,
        withdraw_won=5000000,
        withdraw_dollar=3000
    )
    repo.sync_status(updated_status)
    print("✅ 상태 업데이트 완료")

    # 업데이트된 상태 확인
    print("\n[업데이트된 상태 확인]")
    final_status = repo.get_status()
    print(f"최종 상태: {final_status}")
    assert final_status.deposit_won == 20000000, "업데이트 실패"
    assert final_status.deposit_dollar == 15000, "업데이트 실패"
    print(f"순 원화: ₩{final_status.get_net_won():,.0f}")
    print(f"순 달러: ${final_status.get_net_dollar():,.0f}")
    print("✅ 상태 업데이트 확인 완료")

    session.close()
    print("\n✅ Status Repository 테스트 완료\n")


def test_status_calculations():
    """Status 계산 메서드 테스트"""
    print("=" * 60)
    print("Status 계산 메서드 테스트")
    print("=" * 60)

    status = Status(
        deposit_won=13000000,  # 1천3백만원 (1만달러 상당)
        deposit_dollar=5000,   # $5,000
        withdraw_won=2600000,  # 2백6십만원 (2천달러 상당)
        withdraw_dollar=1000   # $1,000
    )

    print(f"\n입금: ₩{status.deposit_won:,.0f} + ${status.deposit_dollar:,.0f}")
    print(f"출금: ₩{status.withdraw_won:,.0f} + ${status.withdraw_dollar:,.0f}")

    # 환율 1300원
    exchange_rate = 1300.0

    print(f"\n[환율: ${exchange_rate:,.0f}원]")
    total_deposit = status.get_total_deposit(exchange_rate)
    total_withdraw = status.get_total_withdraw(exchange_rate)
    net_balance = (status.get_net_won() / exchange_rate) + status.get_net_dollar()

    print(f"총 입금액 (달러 환산): ${total_deposit:,.2f}")
    print(f"총 출금액 (달러 환산): ${total_withdraw:,.2f}")
    print(f"순 잔액 (달러 환산): ${net_balance:,.2f}")

    # 검증
    assert abs(total_deposit - 15000) < 0.01, "총 입금액 계산 오류"
    assert abs(total_withdraw - 3000) < 0.01, "총 출금액 계산 오류"
    assert abs(net_balance - 12000) < 0.01, "순 잔액 계산 오류"

    print("\n✅ Status 계산 메서드 테스트 완료\n")


if __name__ == "__main__":
    test_status_creation()
    test_status_repository()
    test_status_calculations()

    print("=" * 60)
    print("✅ 모든 Status 테스트 통과!")
    print("=" * 60)
