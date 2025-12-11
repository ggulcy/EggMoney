"""Overview Usecase - Overview 서버 연동"""
from typing import Optional, Dict, Any, List

from data.external.overview.overview_service import OverviewService
from data.external.overview.models import StockItem
from domain.repositories.status_repository import StatusRepository
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository
from domain.entities.status import Status
from data.external.hantoo import HantooService


class OverviewUsecase:
    """Overview 서버 연동 Usecase"""

    def __init__(
        self,
        status_repo: StatusRepository = None,
        bot_info_repo: BotInfoRepository = None,
        trade_repo: TradeRepository = None,
        hantoo_service: HantooService = None
    ):
        """
        Overview Usecase 초기화

        Args:
            status_repo: Status 리포지토리 (sync_status 사용 시 필요)
            bot_info_repo: BotInfo 리포지토리 (get_balance_data 사용 시 필요)
            trade_repo: Trade 리포지토리 (get_balance_data 사용 시 필요)
            hantoo_service: 한투 서비스 (get_balance_data 사용 시 필요)
        """
        self.service = OverviewService()
        self.status_repo = status_repo
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.hantoo_service = hantoo_service

    def get_deposit_info(self) -> Optional[Dict[str, Any]]:
        """
        Overview 서버에서 입출금 정보 조회

        Returns:
            Dict: 입출금 정보
                {
                    "status": "ok",
                    "owner": "chan",
                    "project": "EggMoney",
                    "data": {
                        "deposit_krw": 원화 입금 합계,
                        "withdraw_krw": 원화 출금 합계,
                        "deposit_usd": 달러 입금 합계,
                        "withdraw_usd": 달러 출금 합계,
                        "net_deposit_krw": 원화 순입금,
                        "net_deposit_usd": 달러 순입금
                    }
                }
            또는 None (실패 시)
        """
        return self.service.get_deposit_info()

    def sync_status(self) -> bool:
        """
        Overview 서버에서 입출금 정보를 가져와 Status DB에 동기화

        Returns:
            bool: 성공 여부
        """
        if not self.status_repo:
            print("StatusRepository가 설정되지 않았습니다")
            return False

        try:
            deposit_info = self.service.get_deposit_info()
            if not deposit_info or deposit_info.get("status") != "ok":
                print("Overview 서버에서 입출금 정보를 가져오지 못했습니다")
                return False

            data = deposit_info.get("data", {})
            status = Status(
                deposit_won=data.get("deposit_krw", 0),
                deposit_dollar=data.get("deposit_usd", 0),
                withdraw_won=data.get("withdraw_krw", 0),
                withdraw_dollar=data.get("withdraw_usd", 0)
            )

            self.status_repo.sync_status(status)
            print(f"Status 동기화 완료: Deposit={status.deposit_won:,.0f}₩ / {status.deposit_dollar:,.2f}$, Withdraw={status.withdraw_won:,.0f}₩ / {status.withdraw_dollar:,.2f}$")
            return True

        except Exception as e:
            print(f"Status 동기화 실패: {str(e)}")
            return False

    def _get_balance_data(self) -> Optional[Dict[str, Any]]:
        """
        잔고 데이터 조회 (Overview 서버 전송용)

        Returns:
            Dict: 잔고 데이터
                {
                    "stock_items": List[StockItem],  # 보유 종목 리스트
                    "total_balance": float,          # 예수금
                    "current_prices": Dict[str, float]  # 티커별 현재가
                }
            또는 None (실패 시)
        """
        if not self.bot_info_repo or not self.trade_repo or not self.hantoo_service:
            print("get_balance_data: 필요한 의존성이 설정되지 않았습니다")
            return None

        try:
            bot_info_list = self.bot_info_repo.find_all()
            stock_items = []
            current_prices = {}

            # 각 봇의 거래 정보 수집
            for bot_info in bot_info_list:
                trade = self.trade_repo.find_by_name(bot_info.name)
                if trade and trade.amount > 0:
                    stock_items.append(StockItem(
                        name=bot_info.name,
                        ticker=trade.symbol,
                        amount=trade.amount,
                        price=trade.purchase_price,
                        total_price=trade.total_price
                    ))
                    # 현재가 조회
                    if trade.symbol not in current_prices:
                        price = self.hantoo_service.get_price(trade.symbol)
                        if price:
                            current_prices[trade.symbol] = price

            # RP 추가
            rp_trade = self.trade_repo.find_by_name("RP")
            if rp_trade and rp_trade.purchase_price != 0:
                stock_items.append(StockItem(
                    name="RP",
                    ticker=rp_trade.symbol,
                    amount=rp_trade.amount,
                    price=rp_trade.purchase_price,
                    total_price=rp_trade.total_price
                ))

            # 총 잔고(예수금) 조회
            total_balance = self.hantoo_service.get_balance()
            if total_balance is None:
                total_balance = 0.0

            return {
                "stock_items": stock_items,
                "total_balance": total_balance,
                "current_prices": current_prices
            }

        except Exception as e:
            print(f"잔고 데이터 조회 실패: {str(e)}")
            return None

    def sync_portfolio(self) -> bool:
        """
        잔고 데이터를 조회하여 Overview 서버에 전송

        Returns:
            bool: 성공 여부
        """
        try:
            # 1. 잔고 데이터 조회
            balance_data = self._get_balance_data()
            if not balance_data:
                print("잔고 데이터를 조회하지 못했습니다")
                return False

            # 2. Overview 서버에 전송
            success = self.service.post_portfolio(
                stock_items=balance_data["stock_items"],
                total_balance=balance_data["total_balance"],
                current_prices=balance_data["current_prices"]
            )

            if success:
                print(f"Portfolio 동기화 완료: {len(balance_data['stock_items'])}개 종목, 예수금 ${balance_data['total_balance']:,.2f}")
            else:
                print("Portfolio 동기화 실패")

            return success

        except Exception as e:
            print(f"Portfolio 동기화 실패: {str(e)}")
            return False
