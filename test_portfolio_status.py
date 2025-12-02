#!/usr/bin/env python3
"""포트폴리오 스테이터스 유즈케이스 테스트"""

import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import item
from data.persistence.sqlalchemy.core import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
    SQLAlchemyStatusRepository
)
from data.external.hantoo import HantooService
from data.external.sheets import SheetsService
from usecase.portfolio_status_usecase import PortfolioStatusUsecase
from presentation.scheduler.message_jobs import MessageJobs


def initialize_dependencies():
    """의존성 초기화"""
    print("[1단계] 의존성 초기화...")
    print("-" * 80)

    # 세션 팩토리 (None 전달 시 자동으로 egg_{admin}.db 사용)
    session_factory = SessionFactory()
    session = session_factory.create_session()

    # 리포지토리 (Session 객체 전달)
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)

    # Hantoo 서비스 (test_mode 전달)
    hantoo_service = HantooService(test_mode=item.is_test)

    # Sheets 서비스
    sheets_service = SheetsService()

    # 포트폴리오 유즈케이스
    portfolio_usecase = PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        sheets_service=sheets_service
    )

    print("✅ 의존성 초기화 완료")
    print()

    return session, portfolio_usecase, bot_info_repo


def test_trade_status(portfolio_usecase, bot_info_repo):
    """거래 상태 조회 테스트"""
    print("[2단계] 거래 상태 조회 테스트...")
    print("-" * 80)

    bot_info_list = bot_info_repo.find_all()
    print(f"총 {len(bot_info_list)}개 봇 발견")

    for bot_info in bot_info_list:
        print(f"\n📍 봇 이름: {bot_info.name} ({bot_info.symbol})")
        trade_status = portfolio_usecase.get_trade_status(bot_info)

        if trade_status:
            print(f"  - 현재가: ${trade_status['cur_price']:,.2f}")
            print(f"  - 평단가: ${trade_status['cur_trade']['purchase_price']:,.2f}")
            print(f"  - 보유량: {trade_status['cur_trade']['amount']}주")
            print(f"  - 손익: ${trade_status['profit']:,.2f} ({trade_status['profit_rate']:.2f}%)")
            print(f"  - T: {trade_status['t']:.2f}T / {bot_info.max_tier:.2f}T")
            print(f"  - 진행률: {trade_status['progress_rate']:.2f}%")
        else:
            print("  - 거래 데이터 없음")

    print()
    print("✅ 거래 상태 조회 완료")
    print()


def test_portfolio_summary(portfolio_usecase):
    """포트폴리오 요약 조회 테스트"""
    print("[3단계] 포트폴리오 요약 조회 테스트...")
    print("-" * 80)

    summary = portfolio_usecase.get_portfolio_summary()

    if summary:
        print(f"  - 예수금: ${summary['hantoo_balance']:,.2f}")
        print(f"  - 주식 평가액: ${summary['invest']:,.2f}")
        print(f"  - RP: ${summary['rp']:,.2f}")
        print(f"  - 잔고 총합: ${summary['total_balance']:,.2f}")
        print(f"  - 투자금: ${summary['total_buy']:,.2f}")
        print(f"  - 현재 손익: ${summary['current_profit']:,.2f}")
        print(f"  - 누적 수익: ${summary['total_profit']:,.2f}")
        print(f"  - 출금 가능액: ${summary['pool']:,.2f}")
        print(f"  - 활성 봇: {summary['active_bots']}/{summary['total_bots']}")
        print(f"  - 현금비율: {100 - summary['process_rate']:.2f}%")
        print(f"\n{summary['progress_bar']}\n")
    else:
        print("⚠️ 포트폴리오 요약 데이터 없음")

    print("✅ 포트폴리오 요약 조회 완료")
    print()


def test_today_profit(portfolio_usecase):
    """오늘의 수익 조회 테스트"""
    print("[4단계] 오늘의 수익 조회 테스트...")
    print("-" * 80)

    profit_data = portfolio_usecase.get_today_profit()

    if profit_data and profit_data['has_profit']:
        print(f"  - 총 수익: ${profit_data['total_profit']:,.2f}")
        print(f"  - 거래 건수: {len(profit_data['details'])}건")
        for detail in profit_data['details']:
            print(f"    [{detail['name']}] → ${detail['profit']:,.2f}")
    else:
        print("  - 오늘 수익 없음")

    print()
    print("✅ 오늘의 수익 조회 완료")
    print()


def test_telegram_messages(portfolio_usecase):
    """텔레그램 메시지 전송 테스트 (개별 메서드)"""
    print("[5단계] 텔레그램 메시지 전송 테스트...")
    print("-" * 80)

    # 5-1. 거래 상태 메시지
    print("\n📨 [5-1] 거래 상태 메시지 전송...")
    MessageJobs.send_trade_status_message(portfolio_usecase)

    # 5-2. 포트폴리오 요약 메시지
    print("\n📨 [5-2] 포트폴리오 요약 메시지 전송...")
    MessageJobs.send_portfolio_summary_message(portfolio_usecase)

    # 5-3. 오늘의 수익 메시지
    print("\n📨 [5-3] 오늘의 수익 메시지 전송...")
    MessageJobs.send_today_profit_message(portfolio_usecase)

    print()
    print("✅ 텔레그램 메시지 전송 완료")
    print()


# ========================================
# egg 스타일 래퍼 함수 (간편 사용)
# ========================================

def cur_trade_status(portfolio_usecase):
    """
    거래 상태 조회 + 텔레그램 전송 (egg 스타일)

    egg의 status_repository.cur_trade_status()와 동일
    """
    MessageJobs.cur_trade_status(portfolio_usecase)


def cur_history_status(portfolio_usecase):
    """
    포트폴리오 요약 조회 + 텔레그램 전송 (egg 스타일)

    egg의 status_repository.cur_history_status()와 동일
    """
    MessageJobs.cur_history_status(portfolio_usecase)


def today_profit(portfolio_usecase):
    """
    오늘의 수익 조회 + 텔레그램 전송 (egg 스타일)

    egg의 status_repository.today_profit()와 동일
    """
    MessageJobs.today_profit(portfolio_usecase)


def send_all_status(portfolio_usecase):
    """
    모든 상태 메시지 한번에 전송

    거래 상태 + 포트폴리오 요약 + 오늘 수익
    """
    MessageJobs.send_all_status(portfolio_usecase)


def main():
    """메인 테스트 함수"""
    print("=" * 80)
    print("포트폴리오 스테이터스 유즈케이스 테스트")
    print(f"테스트 모드: {item.is_test}")
    print(f"관리자: {item.admin.value}")
    print("=" * 80)
    print()

    # 의존성 초기화
    session, portfolio_usecase, bot_info_repo = initialize_dependencies()

    try:
        # ===== 방법 1: 개별 테스트 (상세 확인용) =====
        # test_trade_status(portfolio_usecase, bot_info_repo)
        # test_portfolio_summary(portfolio_usecase)
        # test_today_profit(portfolio_usecase)
        # test_telegram_messages(portfolio_usecase)

        # ===== 방법 2: egg 스타일 (간편 사용) =====
        print("\n" + "=" * 80)
        print("egg 스타일 테스트 (조회 + 전송 한번에)")
        print("=" * 80 + "\n")

        # 개별 호출
        # cur_trade_status(portfolio_usecase)
        # cur_history_status(portfolio_usecase)
        # today_profit(portfolio_usecase)

        # 또는 한번에 전송
        send_all_status(portfolio_usecase)

        # 테스트 완료
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)

    finally:
        # 세션 종료
        session.close()


if __name__ == "__main__":
    main()
