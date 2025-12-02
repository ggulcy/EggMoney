#!/usr/bin/env python3
"""
Google Sheets 동기화 테스트

egg/ValueRebalancing의 시트 동기화 기능 테스트
"""

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


def setup():
    """의존성 초기화"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    hantoo_service = HantooService(test_mode=item.is_test)
    sheets_service = SheetsService()

    portfolio_usecase = PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        sheets_service=sheets_service
    )

    return session, portfolio_usecase


# ========================================
# 시트 동기화 함수
# ========================================

def sync_balance_to_sheets():
    """잔고를 Google Sheets에 동기화"""
    session, portfolio_usecase = setup()
    try:
        print("📝 잔고를 Google Sheets에 동기화 중...")
        message_jobs = MessageJobs(portfolio_usecase=portfolio_usecase)
        message_jobs.sync_balance_to_sheets()
        print("✅ 완료!")
    finally:
        session.close()


def sync_status_from_sheets():
    """Google Sheets에서 입금액 정보 읽어서 Status DB 동기화"""
    session, portfolio_usecase = setup()
    try:
        print("📥 Google Sheets에서 입금액 정보 읽기...")
        message_jobs = MessageJobs(portfolio_usecase=portfolio_usecase)
        message_jobs.sync_status_from_sheets()
        print("✅ 완료!")
    finally:
        session.close()


def sync_all_sheets():
    """모든 시트 동기화 (잔고 쓰기 + 입금액 읽기)"""
    session, portfolio_usecase = setup()
    try:
        print("📊 전체 시트 동기화 중...")
        message_jobs = MessageJobs(portfolio_usecase=portfolio_usecase)
        message_jobs.sync_all_sheets()
        print("✅ 완료!")
    finally:
        session.close()


# ========================================
# 메인 실행
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("EggMoney Google Sheets 동기화 테스트")
    print(f"관리자: {item.admin.value}")
    print(f"테스트 모드: {item.is_test}")
    print("=" * 80)
    print()

    # 원하는 함수 선택해서 실행
    sync_balance_to_sheets()     # 현재 잔고를 Google Sheets에 작성
    sync_status_from_sheets()    # Google Sheets에서 입금액 정보 읽어서 DB 동기화
    # sync_all_sheets()              # 모든 시트 동기화

    print()
    print("=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
