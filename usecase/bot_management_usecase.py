"""봇 관리 Usecase - 봇 정보 조회/수정 및 자동화 로직"""
from typing import List, Dict, Any, Optional, Tuple

from config import item, util
from data.external import send_message_sync
from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository


class BotManagementUsecase:
    """봇 관리 Usecase"""

    def __init__(
        self,
        bot_info_repo: BotInfoRepository,
        trade_repo: TradeRepository
    ):
        """
        봇 관리 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo

    # ===== 봇 자동화 관리 =====

    def check_bot_sync(self):
        """
        T 값에 따라 평단가 구매 조건 자동 활성화/비활성화

        - T >= max_tier * 1/3: 평단가 구매 조건 활성화
        - T < max_tier * 1/3: 평단가 구매 조건 비활성화
        - SK 계정은 체크 스킵
        - 변경 사항은 텔레그램으로 알림

        egg/trade_module.py의 check_bot_sync() 이관
        """
        # SK 계정은 bot sync 체크를 하지 않음
        if item.admin == item.BotAdmin.SK:
            return

        bot_infos = self.bot_info_repo.find_all()
        for bot_info in bot_infos:
            if not bot_info.active:
                continue

            point_price, t, point = self._get_point_price(bot_info)

            # T가 1/3을 초과하면 평단가 구매 조건 활성화
            if t >= bot_info.max_tier * 1 / 3 and not bot_info.is_check_buy_avr_price:
                send_message_sync(f"{bot_info.name}의 T가 1/3을 초과 하여 평단가 구매 조건을 활성화 합니다")
                bot_info.is_check_buy_avr_price = True
                self.bot_info_repo.save(bot_info)

            # T가 1/3 이하면 평단가 구매 조건 비활성화
            elif t < bot_info.max_tier * 1 / 3 and bot_info.is_check_buy_avr_price:
                send_message_sync(f"{bot_info.name}의 T가 1/3 이하라 평단가 구매 조건을 비활성화 합니다")
                bot_info.is_check_buy_avr_price = False
                self.bot_info_repo.save(bot_info)

    # ===== 봇 정보 조회/수정 (라우터용) =====

    def get_all_bot_info_with_t(self) -> List[Dict[str, Any]]:
        """
        모든 봇 정보 + T값 조회 (라우터용)

        Returns:
            List[Dict]: 봇 정보 + T값
                [
                    {
                        "bot_info": BotInfo,
                        "t": float
                    },
                    ...
                ]

        egg/routes/bot_info_routes.py의 bot_info_template() 참고 (21-24번 줄)
        """
        bot_infos = self.bot_info_repo.find_all()
        result = []

        for bot_info in bot_infos:
            total_investment = self.trade_repo.get_total_investment(bot_info.name)
            t = util.get_T(total_investment, bot_info.seed)
            result.append({
                "bot_info": bot_info,
                "t": t
            })

        return result

    def update_bot_info(self, bot_info: BotInfo) -> None:
        """
        봇 정보 업데이트 (라우터용)

        Args:
            bot_info: 수정할 봇 정보

        egg/repository/bot_info_repository.py의 sync_bot_info() 참고
        """
        self.bot_info_repo.save(bot_info)

    def get_bot_info_by_name(self, name: str) -> Optional[BotInfo]:
        """
        이름으로 봇 정보 조회

        Args:
            name: 봇 이름 (예: TQ_1)

        Returns:
            봇 정보 또는 None
        """
        return self.bot_info_repo.find_by_name(name)

    def delete_bot_info(self, name: str) -> None:
        """
        봇 정보 삭제 (라우터용)

        Args:
            name: 삭제할 봇 이름
        """
        self.bot_info_repo.delete(name)

    # ===== 내부 헬퍼 메서드 =====

    def _get_point_price(self, bot_info: BotInfo) -> Tuple[Optional[float], float, float]:
        """
        %지점가, T, point 계산 (내부 헬퍼)

        Args:
            bot_info: 봇 정보

        Returns:
            (point_price, t, point) 튜플
            - point_price: %지점가 (평단가 * (1 + point)), avr_price가 없으면 None
            - t: T 값 (총 투자금 / seed)
            - point: % 지점 (예: 0.05 = 5%)

        egg/trade_module.py의 get_point_price() 이관 (249-256번 줄)
        """
        total_investment = self.trade_repo.get_total_investment(bot_info.name)
        t = util.get_T(total_investment, bot_info.seed)
        point = util.get_point_loc(bot_info.t_div, bot_info.max_tier, t, bot_info.point_loc)

        avr_price = self.trade_repo.get_average_purchase_price(bot_info.name)
        if avr_price:
            point_price = round(avr_price * (1 + point), 2)
            return point_price, t, point
        else:
            return None, 0, 0
