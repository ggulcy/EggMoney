# -*- coding: utf-8 -*-
"""Exchange Repository Interface - 증권사 API 추상화"""
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from domain.value_objects import TradeResult
    from data.external.hantoo.hantoo_models import BalanceResult, TickerItem


class ExchangeRepository(ABC):
    """
    증권사 거래 API 인터페이스

    증권사 API(한투, 키움 등)를 추상화하여 비즈니스 로직에서
    구현체에 의존하지 않도록 함
    """

    # === 가격 조회 ===

    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        """
        현재 가격 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 현재 가격, 조회 실패 시 None
        """
        ...

    @abstractmethod
    def get_prev_price(self, symbol: str) -> Optional[float]:
        """
        전일 종가 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 전일 종가, 조회 실패 시 None
        """
        ...

    @abstractmethod
    def get_available_buy(self, symbol: str) -> Optional[float]:
        """
        매수 주문 가능 가격 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 매수 주문 가능 가격
        """
        ...

    @abstractmethod
    def get_available_sell(self, symbol: str) -> Optional[float]:
        """
        매도 주문 가능 가격 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 매도 주문 가능 가격
        """
        ...

    # === 주문 실행 ===

    @abstractmethod
    def buy(self, symbol: str, amount: float, request_price: float) -> Optional['TradeResult']:
        """
        즉시 매수 (주문 후 체결 확인까지 대기)

        Args:
            symbol: 종목 심볼
            amount: 매수 수량
            request_price: 주문 가격

        Returns:
            TradeResult: 거래 결과, 실패 시 None
        """
        ...

    @abstractmethod
    def sell(self, symbol: str, amount: float, request_price: float) -> Optional['TradeResult']:
        """
        즉시 매도 (주문 후 체결 확인까지 대기)

        Args:
            symbol: 종목 심볼
            amount: 매도 수량
            request_price: 주문 가격

        Returns:
            TradeResult: 거래 결과, 실패 시 None
        """
        ...

    @abstractmethod
    def buy_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]:
        """
        매수 주문만 (주문번호만 반환, TWAP용)

        Args:
            symbol: 종목 심볼
            amount: 매수 수량
            request_price: 주문 가격

        Returns:
            str: 주문번호 (ODNO), 실패 시 None
        """
        ...

    @abstractmethod
    def sell_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]:
        """
        매도 주문만 (주문번호만 반환, TWAP용)

        Args:
            symbol: 종목 심볼
            amount: 매도 수량
            request_price: 주문 가격

        Returns:
            str: 주문번호 (ODNO), 실패 시 None
        """
        ...

    # === 포트폴리오 조회 ===

    @abstractmethod
    def get_amount_data(self, symbol: str) -> Optional['BalanceResult']:
        """
        잔고 데이터 조회

        Args:
            symbol: 종목 심볼

        Returns:
            BalanceResult: 잔고 데이터
        """
        ...

    @abstractmethod
    def get_balance(self, symbol: str, price: float) -> float:
        """
        주문 가능 금액 조회

        Args:
            symbol: 종목 심볼
            price: 가격

        Returns:
            float: 주문 가능 금액
        """
        ...

    @abstractmethod
    def get_ticker_list_info(self, ticker_list: List[str]) -> List['TickerItem']:
        """
        종목 목록별 정보 조회

        Args:
            ticker_list: 조회할 종목 목록

        Returns:
            List[TickerItem]: 종목 정보 목록
        """
        ...

    @abstractmethod
    def get_amount_ticker_balance(self, ticker_list: List[str]) -> List['TickerItem']:
        """
        티커별 잔고 조회

        Args:
            ticker_list: 조회할 종목 목록

        Returns:
            List[TickerItem]: 티커별 잔고 정보
        """
        ...
