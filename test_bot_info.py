"""BotInfo 테스트 스크립트"""
import sys
import os

# EggMoney 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.entities.bot_info import BotInfo
from domain.value_objects.point_loc import PointLoc
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories.bot_info_repository_impl import SQLAlchemyBotInfoRepository


def test_bot_info():
    print("=" * 60)
    print("BotInfo Clean Architecture 테스트")
    print("=" * 60)

    # 1. SessionFactory 생성
    print("\n[1] SessionFactory 생성...")
    session_factory = SessionFactory()
    session = session_factory.create_session()
    print(f"✅ 세션 생성 완료: {session}")

    # 2. Repository 생성 (DI 패턴)
    print("\n[2] Repository 생성 (Dependency Injection)...")
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    print("✅ Repository 생성 완료")

    # 3. BotInfo Entity 생성
    print("\n[3] BotInfo Entity 생성...")
    bot_info = BotInfo(
        name="test_bot_1",
        symbol="SOXL",
        seed=1000.0,
        profit_rate=0.05,
        t_div=4,
        max_tier=5,
        active=True,
        is_check_buy_avr_price=True,
        is_check_buy_t_div_price=True,
        point_loc=PointLoc.P1,
        added_seed=0.0,
        skip_sell=False
    )
    print(f"✅ Entity 생성: {bot_info}")

    # 4. Repository를 통해 저장
    print("\n[4] Repository.save() - 신규 저장...")
    bot_info_repo.save(bot_info)
    print("✅ DB 저장 완료")

    # 5. 조회
    print("\n[5] Repository.find_by_name()...")
    found = bot_info_repo.find_by_name("test_bot_1")
    print(f"✅ 조회 결과: {found}")
    print(f"   - seed: {found.seed}, added_seed: {found.added_seed}")
    print(f"   - total_seed: {found.get_total_seed()}")

    # 6. Entity 메서드 호출 (update_added_seed)
    print("\n[6] Entity.update_added_seed(500) 호출...")
    found.update_added_seed(500)
    print(f"✅ Entity 상태 변경 완료 (메모리)")
    print(f"   - seed: {found.seed}, added_seed: {found.added_seed}")
    print(f"   - total_seed: {found.get_total_seed()}")

    # 7. Repository를 통해 다시 저장 (Late Commit)
    print("\n[7] Repository.save() - 업데이트 저장...")
    bot_info_repo.save(found)
    print("✅ DB 저장 완료")

    # 8. 다시 조회해서 확인
    print("\n[8] 재조회로 DB 반영 확인...")
    found_again = bot_info_repo.find_by_name("test_bot_1")
    print(f"✅ 조회 결과: {found_again}")
    print(f"   - seed: {found_again.seed}, added_seed: {found_again.added_seed}")
    print(f"   - total_seed: {found_again.get_total_seed()}")

    # 9. find_by_symbol 테스트
    print("\n[9] Repository.find_by_symbol('SOXL')...")
    soxl_bots = bot_info_repo.find_by_symbol("SOXL")
    print(f"✅ SOXL 봇 개수: {len(soxl_bots)}")

    # 10. find_active_bots 테스트
    print("\n[10] Repository.find_active_bots()...")
    active_bots = bot_info_repo.find_active_bots()
    print(f"✅ 활성 봇 개수: {len(active_bots)}")

    # 11. 정리
    print("\n[11] 테스트 데이터 삭제...")
    bot_info_repo.delete("test_bot_1")
    print("✅ 삭제 완료")

    session.close()
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60)


if __name__ == "__main__":
    test_bot_info()
