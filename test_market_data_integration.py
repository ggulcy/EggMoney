#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시장 지표 통합 테스트 - PortfolioStatusUsecase.get_market_data() 테스트"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.external.market_data.market_indicator_repository_impl import MarketIndicatorRepositoryImpl
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
    SQLAlchemyStatusRepository,
)
from data.external.hantoo import HantooService
from data.external.sheets import SheetsService
from usecase.portfolio_status_usecase import PortfolioStatusUsecase
from config import item

print("=" * 80)
print("시장 지표 통합 테스트")
print("=" * 80 + "\n")

# 1. Dependencies 초기화
print("1️⃣  Dependencies 초기화")
print("-" * 80)

session_factory = SessionFactory()
session = session_factory.create_session()

bot_info_repo = SQLAlchemyBotInfoRepository(session)
trade_repo = SQLAlchemyTradeRepository(session)
history_repo = SQLAlchemyHistoryRepository(session)
status_repo = SQLAlchemyStatusRepository(session)

hantoo_service = HantooService(test_mode=item.is_test)
sheets_service = SheetsService()
market_indicator_repo = MarketIndicatorRepositoryImpl()

print("✅ Dependencies 초기화 완료\n")

# 2. PortfolioStatusUsecase 생성 (MarketIndicatorRepository 주입)
print("2️⃣  PortfolioStatusUsecase 생성")
print("-" * 80)

portfolio_usecase = PortfolioStatusUsecase(
    bot_info_repo=bot_info_repo,
    trade_repo=trade_repo,
    history_repo=history_repo,
    status_repo=status_repo,
    hantoo_service=hantoo_service,
    sheets_service=sheets_service,
    market_indicator_repo=market_indicator_repo,
)

print("✅ PortfolioStatusUsecase 생성 완료\n")

# 3. get_market_data() 호출
print("3️⃣  get_market_data() 호출")
print("-" * 80 + "\n")

market_data = portfolio_usecase.get_market_data()

if market_data:
    print("✅ 시장 지표 데이터 조회 성공!\n")

    # VIX 정보
    if "vix" in market_data:
        vix = market_data["vix"]
        print("🔥 VIX 공포 지수")
        print(f"   값: {vix['value']:.2f}")
        print(f"   상태: {vix['level']}")
        print(f"   캐시 생성 시간: {vix['cached_at']}")
        print(f"   경과 시간: {vix['elapsed_hours']:.2f}시간\n")

    # RSI 정보 (동적으로 ticker별 출력)
    if "rsi_data" in market_data:
        rsi_data = market_data["rsi_data"]
        print(f"📈 등록된 봇 Ticker RSI ({len(rsi_data)}개)")
        for ticker, rsi in rsi_data.items():
            print(f"\n   [{ticker}]")
            print(f"   값: {rsi['value']:.2f}")
            print(f"   상태: {rsi['level']}")
            print(f"   캐시 생성 시간: {rsi['cached_at']}")
            print(f"   경과 시간: {rsi['elapsed_hours']:.2f}시간")

    # 4. 텔레그램 메시지 형식 미리보기
    print("\n4️⃣  텔레그램 메시지 형식 미리보기")
    print("-" * 80 + "\n")

    msg_parts = ["📊 시장 지표\n"]

    if "vix" in market_data:
        vix = market_data["vix"]
        msg_parts.append(
            f"🔥 VIX 공포 지수 (갱신: {vix['elapsed_hours']:.1f}시간 전)\n"
            f"  값: {vix['value']:.2f}\n"
            f"  상태: {vix['level']}\n"
        )

    # RSI 정보 (동적으로 ticker별 출력)
    if "rsi_data" in market_data:
        rsi_data = market_data["rsi_data"]
        for ticker, rsi in rsi_data.items():
            msg_parts.append(
                f"\n📈 {ticker} RSI (갱신: {rsi['elapsed_hours']:.1f}시간 전)\n"
                f"  값: {rsi['value']:.2f}\n"
                f"  상태: {rsi['level']}"
            )
            # 마지막 항목이 아니면 줄바꿈 추가
            if ticker != list(rsi_data.keys())[-1]:
                msg_parts.append("\n")

    full_msg = "".join(msg_parts)
    print("=" * 40)
    print(full_msg)
    print("=" * 40)

else:
    print("❌ 시장 지표 데이터 조회 실패")

print("\n" + "=" * 80)
print("✅ 통합 테스트 완료!")
print("\n💡 MessageJobs.daily_job()에서 자동으로 시장 지표를 조회하여 텔레그램으로 전송합니다")
print("=" * 80 + "\n")
