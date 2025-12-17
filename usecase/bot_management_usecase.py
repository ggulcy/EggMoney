"""봇 관리 Usecase - 봇 정보 조회/수정 및 자동화 로직"""
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from config import item, util
from config.util import get_seed_ratio_by_drawdown
from data.external import send_message_sync
from data.external.hantoo.hantoo_service import HantooService
from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository

if TYPE_CHECKING:
    from usecase.market_usecase import MarketUsecase


class BotManagementUsecase:
    """봇 관리 Usecase"""

    def __init__(
            self,
            bot_info_repo: BotInfoRepository,
            trade_repo: TradeRepository,
            hantoo_service: Optional[HantooService] = None,
            market_usecase: Optional['MarketUsecase'] = None
    ):
        """
        봇 관리 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            hantoo_service: 한투 서비스 (동적 시드 기능용, Optional)
            market_usecase: 마켓 Usecase (drawdown 조회용, Optional)
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.hantoo_service = hantoo_service
        self.market_usecase = market_usecase

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

    def apply_dynamic_seed(self) -> None:
        """
        모든 활성 봇에 대해 동적 시드 적용 (2단계)

        1단계: 전일대비 하락 → 현재 시드에 multiplier 적용
        2단계: 고점대비 하락률 → dynamic_seed_max × ratio 보다 적으면 증가

        데일리잡에서 호출
        """
        if self.hantoo_service is None:
            return

        for bot_info in self.bot_info_repo.find_active_bots():
            # 기능 비활성화 체크
            if bot_info.dynamic_seed_max <= 0:
                continue

            # 이미 max에 도달했으면 스킵
            if bot_info.seed >= bot_info.dynamic_seed_max:
                continue

            # 티커별 하락률 인터벌 (소수)
            drop_interval_rate = 0.03 if bot_info.symbol == "TQQQ" else 0.05

            old_seed = bot_info.seed
            target_seed = old_seed

            # ===== 1단계: 전일대비 하락 =====
            step1_result = self._apply_daily_drop_seed(bot_info, old_seed, drop_interval_rate)
            if step1_result:
                target_seed = step1_result['target_seed']

            # ===== 2단계: 고점대비 하락률 =====
            step2_result = self._apply_drawdown_seed(bot_info, drop_interval_rate)
            if step2_result and step2_result['target_seed'] > target_seed:
                target_seed = step2_result['target_seed']

            # ===== 최종 적용 =====
            target_seed = min(target_seed, bot_info.dynamic_seed_max)

            if target_seed > old_seed:
                bot_info.seed = target_seed
                self.bot_info_repo.save(bot_info)

                # 적용된 트리거 판별
                if step2_result and step2_result['target_seed'] >= target_seed:
                    trigger = step2_result['trigger']
                else:
                    trigger = step1_result['trigger']

                increase_rate = ((target_seed - old_seed) / old_seed) * 100
                send_message_sync(
                    f"📈 [{bot_info.name}] 동적 시드 적용\n"
                    f"{trigger}\n"
                    f"${old_seed:,.2f} → ${target_seed:,.2f} (+{increase_rate:.1f}%)"
                )

    def _apply_daily_drop_seed(
            self,
            bot_info: BotInfo,
            current_seed: float,
            drop_interval_rate: float
    ) -> Optional[Dict[str, Any]]:
        """
        1단계: 전일대비 하락 시 시드 증가

        전일 종가 대비 현재가가 일정 비율 이상 하락했을 때,
        시드를 배수로 증가

        Args:
            bot_info: 봇 정보
            current_seed: 현재 시드
            drop_interval_rate: 하락률 인터벌 (소수, 예: 0.03 → 3%)

        Returns:
            성공 시: {'target_seed': 목표시드, 'trigger': 트리거사유}
            실패 시: None
        """
        MULTIPLIER = 1.2

        if self.hantoo_service is None:
            return None

        prev_close = self.hantoo_service.get_prev_price(bot_info.symbol)
        current_price = self.hantoo_service.get_price(bot_info.symbol)

        if prev_close is None or current_price is None or prev_close <= 0:
            return None

        drop_rate = (prev_close - current_price) / prev_close

        if drop_rate < drop_interval_rate:
            return None

        return {
            'target_seed': current_seed * MULTIPLIER,
            'trigger': f"전일대비 {drop_rate * 100:.1f}% 하락"
        }

    def _apply_drawdown_seed(
            self,
            bot_info: BotInfo,
            drop_interval_rate: float
    ) -> Optional[Dict[str, Any]]:
        """
        2단계: 고점대비 하락률 기반 시드 조정

        90일 고점 대비 하락률로 seed_ratio 계산 후,
        dynamic_seed_max × ratio 값을 목표 시드로 반환

        Args:
            bot_info: 봇 정보
            drop_interval_rate: 하락률 인터벌 (소수, 예: 0.03 → 3%)

        Returns:
            성공 시: {'target_seed': 목표시드, 'trigger': 트리거사유}
            실패 시: None
        """
        if self.market_usecase is None:
            return None

        MAX_COUNT = 10

        # drawdown 조회
        drawdown_result = self.market_usecase.get_drawdown(
            ticker=bot_info.symbol,
            days=90
        )

        if drawdown_result is None:
            return None

        drawdown_rate = drawdown_result['drawdown_rate']

        # seed_ratio 계산
        seed_ratio = get_seed_ratio_by_drawdown(
            drawdown_rate=drawdown_rate,
            interval_rate=drop_interval_rate,
            max_count=MAX_COUNT
        )

        # 목표 시드 계산
        target_seed = bot_info.dynamic_seed_max * seed_ratio

        if target_seed <= 0:
            return None

        return {
            'target_seed': target_seed,
            'trigger': f"고점대비 {drawdown_rate * 100:.1f}% 하락 (ratio: {seed_ratio * 100:.0f}%)"
        }
