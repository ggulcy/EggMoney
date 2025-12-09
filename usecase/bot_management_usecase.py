"""봇 관리 Usecase - 봇 정보 조회/수정 및 자동화 로직"""
from typing import List, Dict, Any, Optional, Tuple

from config import item, util
from data.external import send_message_sync
from data.external.hantoo.hantoo_service import HantooService
from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository


class BotManagementUsecase:
    """봇 관리 Usecase"""

    def __init__(
        self,
        bot_info_repo: BotInfoRepository,
        trade_repo: TradeRepository,
        hantoo_service: Optional[HantooService] = None
    ):
        """
        봇 관리 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            hantoo_service: 한투 서비스 (동적 시드 기능용, Optional)
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.hantoo_service = hantoo_service

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

    # ===== 동적 시드 관리 =====

    def check_and_apply_dynamic_seed(self) -> None:
        """
        모든 활성 봇에 대해 동적 시드 적용 체크 및 적용

        데일리잡에서 호출하여 전일 종가 대비 하락 시 시드 조절
        """
        if self.hantoo_service is None:
            return

        bot_infos = self.bot_info_repo.find_active_bots()

        for bot_info in bot_infos:
            result = self.apply_dynamic_seed(bot_info)
            if result is not None:
                send_message_sync(
                    f"📈 [{bot_info.name}] 동적 시드 적용\n"
                    f"하락률: {result['drop_rate']:.2f}%\n"
                    f"시드: ${result['old_seed']:,.2f} → ${result['new_seed']:,.2f} (+{result['increase_rate']:.1f}%)"
                )

    def apply_dynamic_seed(self, bot_info: BotInfo) -> Optional[Dict[str, Any]]:
        """
        동적 시드 적용

        전일 종가 대비 현재가가 일정 비율 이상 하락했을 때,
        시드를 배수로 늘리고 BotInfo를 업데이트

        Args:
            bot_info: 봇 정보

        Returns:
            성공 시: {
                'old_seed': 이전 시드,
                'new_seed': 새 시드,
                'drop_rate': 하락률%,
                'increase_rate': 증가율%
            }
            실패 시: None
        """
        DROP_RATE_THRESHOLD = 0.03  # 3% 하락 기준
        MULTIPLIER = 1.5            # 1.5배

        # 기능 비활성화 (dynamic_seed_max가 0 이하)
        if bot_info.dynamic_seed_max <= 0:
            return None

        # 기본 시드가 이미 max보다 크면 적용 불필요
        if bot_info.seed >= bot_info.dynamic_seed_max:
            return None

        # hantoo_service 없으면 기능 비활성화
        if self.hantoo_service is None:
            return None

        # 가격 조회
        prev_close = self.hantoo_service.get_prev_price(bot_info.symbol)
        current_price = self.hantoo_service.get_price(bot_info.symbol)

        if prev_close is None or current_price is None or prev_close <= 0:
            return None

        # 하락률 계산
        drop_rate = (prev_close - current_price) / prev_close

        # 기준 미달 → 적용 안함
        if drop_rate < DROP_RATE_THRESHOLD:
            return None

        # 동적 시드 계산 (최대값 제한)
        old_seed = bot_info.seed
        target_seed = old_seed * MULTIPLIER
        target_seed = min(target_seed, bot_info.dynamic_seed_max)

        # seed 직접 수정
        if target_seed > old_seed:
            bot_info.seed = target_seed
            self.bot_info_repo.save(bot_info)

            increase_rate = ((target_seed - old_seed) / old_seed) * 100

            return {
                'old_seed': old_seed,
                'new_seed': target_seed,
                'drop_rate': drop_rate * 100,
                'increase_rate': increase_rate
            }

        return None
