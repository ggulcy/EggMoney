#!/usr/bin/env python3
"""
텔레그램 메시지 전송 테스트

egg 프로젝트의 status_repository처럼 간단하게 사용 가능
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
from usecase.market_analysis_usecase import MarketAnalysisUsecase
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

    market_usecase = MarketAnalysisUsecase()

    return session, portfolio_usecase, market_usecase


# ========================================
# 메시지 전송 함수
# ========================================

def cur_trade_status():
    """거래 상태 메시지 전송"""
    session, portfolio_usecase, market_usecase = setup()
    try:
        print("📨 거래 상태 메시지 전송 중...")
        MessageJobs.cur_trade_status(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def cur_history_status():
    """포트폴리오 요약 메시지 전송 (시장 지표 포함)"""
    session, portfolio_usecase, market_usecase = setup()
    try:
        print("📨 포트폴리오 요약 메시지 전송 중...")
        MessageJobs.cur_history_status(portfolio_usecase, market_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def today_profit():
    """오늘의 수익 메시지 전송"""
    session, portfolio_usecase, market_usecase = setup()
    try:
        print("📨 오늘의 수익 메시지 전송 중...")
        MessageJobs.today_profit(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def send_all():
    """모든 상태 메시지 전송"""
    session, portfolio_usecase, market_usecase = setup()
    try:
        print("📨 모든 상태 메시지 전송 중...")
        MessageJobs.send_all_status(portfolio_usecase, market_usecase)
        print("✅ 완료!")
    finally:
        session.close()


# ========================================
# 메인 실행
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("EggMoney 텔레그램 메시지 전송 테스트")
    print(f"관리자: {item.admin.value}")
    print(f"테스트 모드: {item.is_test}")
    print("=" * 80)
    print()

    # 원하는 함수 선택해서 실행
    # cur_trade_status()           # 거래 상태 메시지만
    # cur_history_status()         # 포트폴리오 요약 메시지만
    # today_profit()               # 오늘의 수익 메시지만
    send_all()                     # 모든 메시지 한번에

    print()
    print("=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
