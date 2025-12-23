# -*- coding: utf-8 -*-
"""
Dependencies Container - 의존성 주입 컨테이너

모든 Repository 및 외부 서비스 의존성을 중앙에서 관리.
앱 시작 시 한 번만 초기화하고, 어디서든 get_dependencies()로 접근.
"""
from dataclasses import dataclass
from typing import Optional

from domain.repositories import (
    BotInfoRepository,
    TradeRepository,
    HistoryRepository,
    OrderRepository,
    ExchangeRepository,
    MessageRepository,
)
from domain.repositories.market_indicator_repository import MarketIndicatorRepository


@dataclass
class Dependencies:
    """애플리케이션 의존성 컨테이너"""

    # === Internal Repositories (DB) ===
    bot_info_repo: BotInfoRepository
    trade_repo: TradeRepository
    history_repo: HistoryRepository
    order_repo: OrderRepository

    # === External Repositories ===
    market_indicator_repo: MarketIndicatorRepository
    exchange_repo: ExchangeRepository
    message_repo: MessageRepository


# 싱글톤 인스턴스
_dependencies: Optional[Dependencies] = None


def init_dependencies(test_mode: bool = False) -> Dependencies:
    """
    의존성 초기화 (앱 시작 시 한 번만 호출)

    Args:
        test_mode: 테스트 모드 여부

    Returns:
        Dependencies: 초기화된 의존성 컨테이너
    """
    global _dependencies

    # 이미 초기화된 경우 기존 인스턴스 반환
    if _dependencies is not None:
        return _dependencies

    # Internal Repository Implementations
    from data.persistence.sqlalchemy.core import SessionFactory
    from data.persistence.sqlalchemy.repositories import (
        SQLAlchemyBotInfoRepositoryImpl,
        SQLAlchemyTradeRepositoryImpl,
        SQLAlchemyHistoryRepositoryImpl,
        SQLAlchemyOrderRepositoryImpl,
    )

    # External Repository Implementations
    from data.external.market_data import MarketIndicatorRepositoryImpl
    from data.external.hantoo import HantooExchangeRepositoryImpl
    from data.external.telegram import TelegramMessageRepositoryImpl

    # 세션 생성
    session = SessionFactory().create_session()

    _dependencies = Dependencies(
        # Internal Repositories
        bot_info_repo=SQLAlchemyBotInfoRepositoryImpl(session),
        trade_repo=SQLAlchemyTradeRepositoryImpl(session),
        history_repo=SQLAlchemyHistoryRepositoryImpl(session),
        order_repo=SQLAlchemyOrderRepositoryImpl(session),
        # External Repositories
        market_indicator_repo=MarketIndicatorRepositoryImpl(),
        exchange_repo=HantooExchangeRepositoryImpl(test_mode=test_mode),
        message_repo=TelegramMessageRepositoryImpl(),
    )

    print(f"[DI] Dependencies initialized (test_mode={test_mode})")
    return _dependencies


def get_dependencies() -> Dependencies:
    """
    의존성 컨테이너 조회 (초기화 후 어디서든 호출 가능)

    Returns:
        Dependencies: 의존성 컨테이너

    Raises:
        RuntimeError: 초기화되지 않은 경우
    """
    if _dependencies is None:
        raise RuntimeError(
            "Dependencies not initialized. Call init_dependencies() first."
        )
    return _dependencies


def reset_dependencies() -> None:
    """
    의존성 컨테이너 초기화 (테스트용)
    """
    global _dependencies
    _dependencies = None
