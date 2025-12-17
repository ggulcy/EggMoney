"""Trading Jobs - 거래 작업 (OrderUsecase + TradingUsecase 조합)

egg/main.py의 job(), twap_job() 이관
- job() → trade_job(): 매매 조건 판단 + 주문서 생성
- twap_job() → twap_job(): TWAP 주문 실행
"""
import time
from datetime import date
from typing import Optional

from config import item
from config.util import is_trade_date
from data.external import send_message_sync
from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.order_repository import OrderRepository
from usecase.bot_management_usecase import BotManagementUsecase
from usecase.order_usecase import OrderUsecase
from usecase.trading_usecase import TradingUsecase


class TradingJobs:
    """
    거래 작업 클래스

    OrderUsecase와 TradingUsecase를 조합하여 전체 거래 플로우 구현
    """

    def __init__(
        self,
        order_usecase: OrderUsecase,
        trading_usecase: TradingUsecase,
        bot_management_usecase: BotManagementUsecase,
        bot_info_repo: BotInfoRepository,
        order_repo: OrderRepository
    ):
        """
        Args:
            order_usecase: 주문서 생성 Usecase
            trading_usecase: 거래 실행 Usecase
            bot_management_usecase: 봇 관리 Usecase
            bot_info_repo: BotInfo 저장소
            order_repo: Order 저장소
        """
        self.order_usecase = order_usecase
        self.trading_usecase = trading_usecase
        self.bot_management_usecase = bot_management_usecase
        self.bot_info_repo = bot_info_repo
        self.order_repo = order_repo

    def trade_job(self) -> None:
        """
        메인 거래 작업 (egg/main.py의 job() 이관)

        - 거래일 체크
        - 오래된 주문서 삭제
        - 활성화된 봇들에 대해 매매 조건 판단 + 주문서 생성

        참고: egg/main.py의 job() (121-143번 줄)
        """
        if not is_trade_date():
            send_message_sync("설정한 거래요일이 아니라 종료 합니다")
            return

        self.bot_management_usecase.check_bot_sync()
        self.bot_management_usecase.apply_dynamic_seed()
        # 오래된 주문서 삭제 (전날 미완료 주문 등)
        self.order_repo.delete_old_orders(before_date=date.today())

        # 혹시 남아있는 완료 주문 체크 (비정상 상황)
        remaining_orders = self.order_repo.find_all()
        if remaining_orders:
            send_message_sync(
                f"⚠️ 메인 거래 시작 전 미처리 주문서 발견!\n"
                f"주문서 개수: {len(remaining_orders)}\n"
                f"주문서 목록: {[o.name for o in remaining_orders]}"
            )

        # 모든 활성 봇에 대해 거래 실행
        bot_infos = self.bot_info_repo.find_all()
        for bot_info in bot_infos:
            if bot_info.active:
                self._execute_trade_for_bot(bot_info)
                if not item.is_test:
                    time.sleep(5)

    def _execute_trade_for_bot(self, bot_info: BotInfo) -> None:
        """
        개별 봇에 대한 거래 실행 (egg/trade_module.py의 trade() 이관)

        Args:
            bot_info: 봇 정보

        참고: egg/trade_module.py의 trade() (25-34번 줄)
        """
        # OrderUsecase를 통해 매매 조건 판단 + 주문 정보 반환
        result = self.order_usecase.create_order(bot_info)

        # 결과가 없으면 종료 (매도/매수 조건 불충족)
        if not result:
            return

        # 결과 언패킹 (매도: (type, amount), 매수: (type, seed))
        trade_type, value = result

        if trade_type.is_buy():
            # 매수 주문서 DB 저장 (value = seed)
            self.order_usecase.save_buy_order(bot_info, value, trade_type)
        elif trade_type.is_sell():
            # 매도 주문서 DB 저장 (value = amount)
            self.order_usecase.save_sell_order(bot_info, int(value), trade_type)

    def twap_job(self) -> None:
        """
        TWAP 거래 작업 (egg/main.py의 twap_job() 이관)

        - 거래일 체크
        - 활성화된 봇 중 주문서가 있는 봇만 TWAP 실행

        참고: egg/main.py의 twap_job() (145-162번 줄)
        """
        if not is_trade_date():
            return

        # 활성화된 봇 중 주문서가 있는 봇만 처리
        for bot_info in self.bot_info_repo.find_all():
            if not bot_info.active:
                continue

            order = self.order_repo.find_by_name(bot_info.name)
            if order:
                # TradingUsecase를 통해 TWAP 주문 1회 실행
                self.trading_usecase.execute_twap(bot_info)
