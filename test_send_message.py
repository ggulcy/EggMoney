#!/usr/bin/env python3
"""
간단한 텔레그램 메시지 전송 테스트

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
from presentation.scheduler.message_jobs import MessageJobs


def setup():
    """의존성 초기화"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    hantoo_service = HantooService(test_mode=item.is_test)  # item.is_test 전달
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
# egg 스타일 간편 함수
# ========================================

def cur_trade_status():
    """거래 상태 메시지 전송"""
    session, portfolio_usecase = setup()
    try:
        print("📨 거래 상태 메시지 전송 중...")
        MessageJobs.cur_trade_status(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def cur_history_status():
    """포트폴리오 요약 메시지 전송"""
    session, portfolio_usecase = setup()
    try:
        print("📨 포트폴리오 요약 메시지 전송 중...")
        MessageJobs.cur_history_status(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def today_profit():
    """오늘의 수익 메시지 전송"""
    session, portfolio_usecase = setup()
    try:
        print("📨 오늘의 수익 메시지 전송 중...")
        MessageJobs.today_profit(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def send_all():
    """모든 상태 메시지 전송"""
    session, portfolio_usecase = setup()
    try:
        print("📨 모든 상태 메시지 전송 중...")
        MessageJobs.send_all_status(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


# ========================================
# 시트 동기화 함수
# ========================================

def sync_balance_to_sheets():
    """잔고를 Google Sheets에 동기화"""
    session, portfolio_usecase = setup()
    try:
        print("📝 잔고를 Google Sheets에 동기화 중...")
        MessageJobs.sync_balance_to_sheets(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def sync_status_from_sheets():
    """Google Sheets에서 입금액 정보 읽어서 Status DB 동기화"""
    session, portfolio_usecase = setup()
    try:
        print("📥 Google Sheets에서 입금액 정보 읽기...")
        MessageJobs.sync_status_from_sheets(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def sync_all_sheets():
    """모든 시트 동기화 (잔고 쓰기 + 입금액 읽기)"""
    session, portfolio_usecase = setup()
    try:
        print("📊 전체 시트 동기화 중...")
        MessageJobs.sync_all_sheets(portfolio_usecase)
        print("✅ 완료!")
    finally:
        session.close()


def daily_job():
    """일일 작업 (메시지 전송 + 시트 동기화)"""
    session, portfolio_usecase = setup()
    try:
        print("📊 일일 작업 실행 중...")
        MessageJobs.daily_job(portfolio_usecase)
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

    # ========================================
    # 📝 사용 방법: 원하는 함수의 주석을 해제하고 실행
    # ========================================

    # ===== 옵션 1: 개별 메시지 전송 =====
    # cur_trade_status()           # 거래 상태 메시지만 전송
    # cur_history_status()         # 포트폴리오 요약 메시지만 전송
    # today_profit()               # 오늘의 수익 메시지만 전송
    # send_all()                   # 위 3개 메시지를 모두 전송

    # ===== 옵션 2: 시트 동기화 (개별 실행) =====
    # sync_balance_to_sheets()     # 현재 잔고를 Google Sheets에 작성
    # sync_status_from_sheets()    # Google Sheets에서 입금액 정보 읽어서 DB 동기화
    # sync_all_sheets()            # 위 2개 시트 동기화를 모두 실행

    # ===== 옵션 3: 일일 작업 (메시지 전송 + 시트 동기화) =====
    daily_job()                    # 추천: 모든 메시지 전송 + 시트 동기화 한번에

    print()
    print("=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
