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

