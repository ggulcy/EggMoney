"""봇 관리 Usecase - 봇 정보 조회/수정 및 자동화 로직"""
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from config import item, util
from domain.entities.bot_info import BotInfo
from domain.repositories import (
    BotInfoRepository,
    TradeRepository,
    ExchangeRepository,
    MessageRepository,
)
from domain.services import bot_factory
from domain.value_objects.point_loc import PointLoc

if TYPE_CHECKING:
    from usecase.market_usecase import MarketUsecase


class BotManagementUsecase:
    """봇 관리 Usecase"""

    def __init__(
            self,
            bot_info_repo: BotInfoRepository,
            trade_repo: TradeRepository,
            exchange_repo: Optional[ExchangeRepository] = None,
            message_repo: Optional[MessageRepository] = None,
            market_usecase: Optional['MarketUsecase'] = None
    ):
        """
        봇 관리 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            exchange_repo: 증권사 API 리포지토리 (동적 시드 기능용, Optional)
            message_repo: 메시지 발송 리포지토리 (Optional)
            market_usecase: 마켓 Usecase (drawdown 조회용, Optional)
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.exchange_repo = exchange_repo
        self.message_repo = message_repo
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
                self.message_repo.send_message(f"{bot_info.name}의 T가 1/3을 초과 하여 평단가 구매 조건을 활성화 합니다")
                bot_info.is_check_buy_avr_price = True
                self.bot_info_repo.save(bot_info)

            # T가 1/3 이하면 평단가 구매 조건 비활성화
            elif t < bot_info.max_tier * 1 / 3 and bot_info.is_check_buy_avr_price:
                self.message_repo.send_message(f"{bot_info.name}의 T가 1/3 이하라 평단가 구매 조건을 비활성화 합니다")
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

    def get_next_bot(self, symbol: str) -> Optional[BotInfo]:
        """
        특정 심볼에 대해 다음 출발할 봇 조회

        Args:
            symbol: 심볼 (예: TQQQ, SOXL)

        Returns:
            다음 출발할 봇 정보 또는 None
            - 거래 내역이 없으면 첫 번째 봇
            - 거래 내역이 있으면 비활성(active=False) 봇 중 첫 번째

        egg/seed_module.py의 get_next_bot() 이관 (272-282번 줄)
        """
        # 해당 심볼의 거래 내역 확인
        exist_trade = self.trade_repo.find_by_symbol(symbol)

        # 해당 심볼의 모든 봇 리스트 조회
        next_bot_list = self.bot_info_repo.find_by_symbol(symbol)

        if not next_bot_list:
            return None

        # 거래 내역이 없으면 첫 번째 봇 반환
        if not exist_trade:
            return next_bot_list[0]

        # 비활성 봇 중 첫 번째 반환
        return next((bot for bot in next_bot_list if not bot.active), None)

    def auto_start_next_bots(self) -> None:
        """
        활성화된 봇들의 심볼을 수집하여 다음 봇 자동 출발

        조건: 현재 활성화된 봇의 T값이 max_tier * 1/3 지점을 통과해야 함

        변화가 있을 때만 텔레그램 메시지 발송

        egg/seed_module.py의 check_is_bot_start() 참고 (475-486번 줄)
        """
        from config import util

        # 1. 활성화된 봇들의 심볼 수집 (중복 제거)
        active_bots = self.bot_info_repo.find_active_bots()
        active_symbols = set(bot.symbol for bot in active_bots)

        # 2. 각 심볼에 대해 다음 봇 찾기 및 활성화
        for symbol in active_symbols:
            next_bot = self.get_next_bot(symbol)

            # 다음 출발할 봇이 없거나 이미 활성화된 경우 스킵 (메시지 없음)
            if next_bot is None or next_bot.active:
                continue

            # 3. T값 조건 체크: 같은 심볼의 활성 봇 중 T값이 가장 낮은 봇이 max_tier * 1/3 통과 여부
            active_bots_for_symbol = [bot for bot in active_bots if bot.symbol == symbol]
            if not active_bots_for_symbol:
                continue

            # 활성 봇 중 T값이 가장 낮은(진행도가 적은) 봇 찾기
            min_t = None
            min_t_bot = None
            for bot in active_bots_for_symbol:
                total_investment = self.trade_repo.get_total_investment(bot.name)
                t = util.get_T(total_investment, bot.seed)
                if min_t is None or t < min_t:
                    min_t = t
                    min_t_bot = bot

            current_t = min_t
            threshold = min_t_bot.max_tier * (1 / 2)

            # T값이 임계값을 통과하지 않았으면 스킵 (메시지 없음)
            if current_t < threshold:
                continue

            # 4. 봇 활성화 (변화 발생)
            next_bot.active = True
            next_bot.is_check_buy_t_div_price = True
            self.bot_info_repo.save(next_bot)

            # 5. 메시지 발송 (변화가 있을 때만)
            if self.message_repo:
                self.message_repo.send_message(
                    f"🚀 자동 봇 출발\n"
                    f"심볼: {symbol}\n"
                    f"봇: {next_bot.name}\n"
                    f"시드: ${next_bot.seed:,.2f}\n"
                    f"Max티어: {next_bot.max_tier}\n"
                    f"현재 T값: {current_t:.2f} (기준: {threshold:.2f})"
                )

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
        모든 활성 봇에 대해 동적 시드 적용

        - 같은 심볼은 한 번만 증액 (시드 작은 봇 우선)
        - T값이 max_tier의 1/3 이상이면 강제 증액
        - 전일대비 하락 시 증액

        데일리잡에서 호출
        """
        if self.exchange_repo is None:
            return

        # 시드 오름차순 정렬 (작은 시드 우선 처리)ㄹ
        bots = self.bot_info_repo.find_active_bots()
        bots.sort(key=lambda x: x.seed)

        processed_symbols = set()  # 증액 완료된 심볼 추적

        for bot_info in bots:
            if self._should_skip_dynamic_seed(bot_info, processed_symbols):
                continue

            applied = self._process_dynamic_seed(bot_info)
            if applied:
                processed_symbols.add(bot_info.symbol)

    def _should_skip_dynamic_seed(self, bot_info: BotInfo, processed_symbols: set) -> bool:
        """동적 시드 스킵 여부 판단"""
        # 기능 비활성화
        if not bot_info.dynamic_seed_enabled:
            return True
        # 이미 max 도달
        if bot_info.seed >= bot_info.dynamic_seed_max:
            return True
        # 이미 증액된 심볼
        if bot_info.symbol in processed_symbols:
            return True
        return False

    def _process_dynamic_seed(self, bot_info: BotInfo) -> bool:
        """
        개별 봇 동적 시드 처리

        Returns:
            증액 적용 여부
        """
        old_seed = bot_info.seed

        # 트리거 체크
        drop_rate = self._get_daily_drop_rate(bot_info)
        t, t_threshold = self._get_t_info(bot_info)

        t_triggered = t >= t_threshold
        drop_triggered = drop_rate is not None and drop_rate >= bot_info.dynamic_seed_drop_rate

        if t_triggered or drop_triggered:
            return self._apply_seed_increase(
                bot_info, old_seed,
                t_triggered, t, t_threshold, drop_rate
            )
        elif drop_rate is not None:
            self._send_no_increase_message(bot_info, old_seed, drop_rate)

        return False

    def _get_daily_drop_rate(self, bot_info: BotInfo) -> Optional[float]:
        """전일대비 하락률 조회"""
        if self.exchange_repo is None:
            return None

        prev_close = self.exchange_repo.get_prev_price(bot_info.symbol)
        current_price = self.exchange_repo.get_price(bot_info.symbol)

        if prev_close is None or current_price is None or prev_close <= 0:
            return None

        return (prev_close - current_price) / prev_close

    def _get_t_info(self, bot_info: BotInfo) -> Tuple[float, float]:
        """T값 및 임계값 계산"""
        total_investment = self.trade_repo.get_total_investment(bot_info.name)
        t = util.get_T(total_investment, bot_info.seed)
        t_threshold = bot_info.max_tier * bot_info.dynamic_seed_t_threshold
        return t, t_threshold

    def _apply_seed_increase(
            self,
            bot_info: BotInfo,
            old_seed: float,
            t_triggered: bool,
            t: float,
            t_threshold: float,
            drop_rate: Optional[float]
    ) -> bool:
        """시드 증액 적용 및 메시지 전송"""
        target_seed = min(old_seed * (1 + bot_info.dynamic_seed_multiplier), bot_info.dynamic_seed_max)

        if target_seed <= old_seed:
            return False

        bot_info.seed = target_seed
        self.bot_info_repo.save(bot_info)

        # 트리거 사유
        if t_triggered:
            trigger = f"T값 {t:.1f} (기준: {t_threshold:.1f} 돌파)"
        else:
            trigger = f"전일대비 {drop_rate * 100:.1f}% 하락"

        increase_rate = ((target_seed - old_seed) / old_seed) * 100

        msg = f"📈 [{bot_info.name}] 동적 시드 적용\n"
        msg += f"트리거: {trigger}\n"
        if drop_rate is not None:
            msg += f"전일대비: {drop_rate * 100:.1f}% {'하락' if drop_rate >= 0 else '상승'}\n"
        msg += f"${old_seed:,.2f} → ${target_seed:,.2f} (+{increase_rate:.1f}%)"

        self.message_repo.send_message(msg)
        return True

    def _send_no_increase_message(self, bot_info: BotInfo, old_seed: float, drop_rate: float) -> None:
        """증액 미적용 시 하락 정보 메시지 전송"""
        self.message_repo.send_message(
            f"📊 [{bot_info.name}] 전일대비 {abs(drop_rate * 100):.1f}% {'하락' if drop_rate >= 0 else '상승'}\n"
            f"현재 시드: ${old_seed:,.2f} (적용 기준 미달)"
        )

    # ===== 봇 팩토리 - 리뉴얼 =====

    def preview_bot_renewal(self, market_stage: int, custom_total_budget: float = None) -> Dict[str, Any]:
        """
        봇 리뉴얼 미리보기 - 변경될 필드만 반환 (DB 저장 안 함)

        Args:
            market_stage: 시장 단계 (0=수비, 1=중립, 2=공격, 3=매우공격)
            custom_total_budget: 사용자 지정 총 예산 (None이면 현재 봇 예산 합계 사용)

        Returns:
            {
                "market_stage": int,
                "total_budget": float,
                "cash_reserve": float,
                "investable": float,
                "bots": [
                    {
                        "name": str,              # 봇 이름 (TQ_1, TQ_2 등)
                        "symbol": str,
                        "seed": float,            # 변경될 시드
                        "max_tier": int,          # 변경될 MaxTier
                        "profit_rate": float,     # 변경될 수익률
                        "point_loc": str,         # 변경될 포인트 위치
                        "level": int,             # 레벨
                        "level_name": str         # 레벨명
                    }
                ]
            }
        """
        # 1. 현재 봇 정보 조회
        current_bots = self.bot_info_repo.find_all()

        if not current_bots:
            return None

        # 2. 현재 상태 분석
        ticker_bot_counts = {}  # {ticker: count}

        # 사용자 지정 예산이 있으면 사용, 없으면 현재 봇 예산 합계 사용
        if custom_total_budget is not None:
            total_budget = custom_total_budget
        else:
            total_budget = 0
            for bot in current_bots:
                # 예산 = seed × max_tier
                bot_budget = bot.seed * bot.max_tier
                total_budget += bot_budget

        for bot in current_bots:
            # 티커별 봇 개수
            ticker_bot_counts[bot.symbol] = ticker_bot_counts.get(bot.symbol, 0) + 1

        # 3. 공통 t_div 추출 (첫 번째 봇의 값 사용)
        common_t_div = current_bots[0].t_div

        # 4. 리뉴얼 봇 설정 생성 (티커별 봇 개수 고정)
        renewal_result = bot_factory.create_bot_configs_for_renewal(
            market_stage=market_stage,
            total_budget=total_budget,
            ticker_bot_counts=ticker_bot_counts,
            t_div=common_t_div
        )

        # 5. 봇 이름을 현재 봇 이름으로 매핑
        renewal_bots = []
        for i, (current_bot, new_config) in enumerate(zip(current_bots, renewal_result["bots"])):
            renewal_bots.append({
                "name": current_bot.name,  # 기존 이름 유지
                "symbol": new_config["symbol"],
                "seed": new_config["seed"],
                "max_tier": new_config["max_tier"],
                "profit_rate": new_config["profit_rate"],
                "point_loc": new_config["point_loc"],
                "level": new_config["level"],
                "level_name": new_config["level_name"]
            })

        return {
            "market_stage": market_stage,
            "total_budget": renewal_result["total_budget"],
            "cash_reserve": renewal_result["cash_reserve"],
            "investable": renewal_result["investable"],
            "bots": renewal_bots
        }

    def apply_bot_renewal(self, market_stage: int, custom_total_budget: float = None) -> Dict[str, Any]:
        """
        봇 리뉴얼 적용 - 실제로 DB에 저장

        Args:
            market_stage: 시장 단계 (0=수비, 1=중립, 2=공격, 3=매우공격)
            custom_total_budget: 사용자 지정 총 예산 (선택사항)

        Returns:
            {
                "updated_count": int,     # 업데이트된 봇 개수
                "bots": List[BotInfo]     # 업데이트된 봇 정보
            }
        """
        # 1. 미리보기로 변경될 설정 조회
        preview = self.preview_bot_renewal(market_stage, custom_total_budget=custom_total_budget)

        if preview is None:
            return {
                "updated_count": 0,
                "bots": []
            }

        # 2. 각 봇의 설정을 업데이트
        updated_bots = []
        for bot_config in preview["bots"]:
            # 봇 정보 조회
            bot_info = self.bot_info_repo.find_by_name(bot_config["name"])

            if bot_info is None:
                continue

            # 필드 업데이트
            bot_info.seed = bot_config["seed"]
            bot_info.max_tier = bot_config["max_tier"]
            bot_info.profit_rate = bot_config["profit_rate"]
            bot_info.point_loc = PointLoc(bot_config["point_loc"])  # str -> Enum 변환

            # 리뉴얼 시 초기화
            bot_info.active = True  # 모두 활성화
            bot_info.dynamic_seed_enabled = False  # 동적 시드 비활성화
            bot_info.dynamic_seed_max = 0.0  # 동적 시드 최대값 초기화
            bot_info.is_check_buy_t_div_price = True
            # added_seed는 유지 (초기화 안 함)

            # DB 저장
            self.bot_info_repo.save(bot_info)
            updated_bots.append(bot_info)

        return {
            "updated_count": len(updated_bots),
            "bots": updated_bots
        }



