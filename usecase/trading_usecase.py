"""매매 실행 Usecase - 매도/매수 조건 판단 및 주문 요청"""
from typing import Optional, Tuple

from config import util
from data.external import send_message_sync
from data.external.hantoo.hantoo_service import HantooService
from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.history_repository import HistoryRepository
from domain.repositories.order_repository import OrderRepository
from domain.repositories.trade_repository import TradeRepository
from domain.value_objects.trade_type import TradeType


class TradingUsecase:
    """매매 실행 Usecase

    egg/trade_module.py 이관
    - 매도/매수 조건 판단
    - 주문 요청 생성 (OrderUsecase로 위임)
    """

    def __init__(
        self,
        bot_info_repo: BotInfoRepository,
        trade_repo: TradeRepository,
        history_repo: HistoryRepository,
        order_repo: OrderRepository,
        hantoo_service: HantooService
    ):
        """
        매매 실행 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            history_repo: History 리포지토리 (오늘 매도 이력 확인)
            order_repo: Order 리포지토리 (오늘 매도 주문 확인)
            hantoo_service: 한투 서비스 (가격 조회)
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.history_repo = history_repo
        self.order_repo = order_repo
        self.hantoo_service = hantoo_service

    # ===== Public Methods (Router/Scheduler에서 호출) =====

    def execute_trading(self, bot_info: BotInfo) -> Optional[tuple]:
        """
        매도 → 매수 순차 실행 (주문 정보 반환)

        Args:
            bot_info: 봇 정보

        Returns:
            Optional[tuple]: (TradeType, value) - 매도는 (type, amount), 매수는 (type, seed)
                           조건 불충족 시 None

        egg/trade_module.py의 trade() 이관 (25-34번 줄)
        """
        # 1. 매도 실행 (skip_sell이 False일 때만)
        if not bot_info.skip_sell:
            result = self._execute_sell(bot_info)
            if result:
                return result

        # 2. 매도가 일어난 날(또는 매도 예정인 날)은 구매하지 않음
        if self.history_repo.find_today_by_name(bot_info.name) or \
           self.order_repo.has_sell_order_today(bot_info.name):
            return None

        # 3. 매수 실행
        return self._execute_buy(bot_info)

    def force_sell(self, bot_info: BotInfo, sell_ratio: float) -> None:
        """
        강제 매도 즉시 실행 (판단 + 실행 + DB 저장)

        Args:
            bot_info: 봇 정보
            sell_ratio: 매도 비율 (0.0 ~ 100.0)

        egg/trade_module.py의 force_sell() 이관 (37-47번 줄)
        - 주문서 생성하지 않고 바로 매도 실행
        - 바로 DB 저장 (Trade, History, BotInfo.added_seed)
        """
        # 1. 조건 판단
        total_amount = self.trade_repo.get_total_amount(bot_info.name)
        sell_amount = int(total_amount * (sell_ratio / 100))
        trade_type = TradeType.SELL if sell_ratio == 100 else TradeType.SELL_PART

        if sell_amount == 0:
            send_message_sync(f"[{bot_info.name}] 판매할 거래가 존재하지 않습니다")
            return

        send_message_sync(f"[{bot_info.name}] 강제 매도 즉시 실행: {sell_amount}주 ({sell_ratio}%)")

        # 2. 현재가 조회
        request_price = self.hantoo_service.get_price(bot_info.symbol)
        if not request_price:
            send_message_sync(f"❌ [{bot_info.name}] 현재가 조회 실패")
            return

        # 3. 매도 실행
        trade_result = self.hantoo_service.sell(
            symbol=bot_info.symbol,
            amount=sell_amount,
            request_price=request_price
        )

        # 4. 거래 결과 확인 및 DB 저장
        if trade_result:
            send_message_sync(f"✅ 강제 매도 체결\n"
                            f"  - 거래유형: {trade_result.trade_type.value}\n"
                            f"  - 체결개수: {trade_result.amount}\n"
                            f"  - 체결가: ${trade_result.unit_price:,.2f}\n"
                            f"  - 총액: ${trade_result.total_price:,.2f}")

            # trade_type을 강제로 설정 (HantooService가 항상 SELL을 반환하므로)
            from domain.value_objects.trade_result import TradeResult
            trade_result = TradeResult(
                trade_type=trade_type,
                amount=trade_result.amount,
                unit_price=trade_result.unit_price,
                total_price=trade_result.total_price
            )

            # DB 저장 (OrderUsecase._save_sell_to_db와 동일한 로직)
            self._save_sell_to_db(bot_info, trade_result)
        else:
            send_message_sync(f"❌ [{bot_info.name}] 강제 매도 실패")

    # ===== Private Methods (내부 헬퍼) =====

    def _execute_sell(self, bot_info: BotInfo) -> Optional[tuple[TradeType, int]]:
        """
        매도 조건 체크 및 실행

        Args:
            bot_info: 봇 정보

        Returns:
            Optional[tuple]: (TradeType, amount) 또는 None

        egg/trade_module.py의 sell() 이관 (50-81번 줄)
        """
        total_amount = self.trade_repo.get_total_amount(bot_info.name)
        avr_price = self.trade_repo.get_average_purchase_price(bot_info.name)

        # 보유량이 0이거나 평단가가 없으면 매도 불가
        if total_amount == 0 or not avr_price:
            return None

        # 현재 상태 조회
        point_price, t, point = self._get_point_price(bot_info)
        cur_price = self.hantoo_service.get_price(bot_info.symbol)
        if not cur_price:
            send_message_sync(f"[{bot_info.name}] 현재가 조회 실패")
            return None

        profit_price = avr_price * (1 + bot_info.profit_rate)

        # 매도 조건 체크
        condition_3_4 = cur_price > profit_price  # 익절가 돌파
        condition_1_4 = cur_price > point_price  # %지점가 돌파

        msg = (f"[🎯판매검사({bot_info.name})] 현재가({cur_price:.2f})\n"
               f"익절가({profit_price:.2f})[{util.get_ox_emoji(condition_3_4)}]\n"
               f"%지점가({point_price:.2f})[{util.get_ox_emoji(condition_1_4)}] ({point * 100:.2f}%)\n")

        # T가 Max 초과 시 손절
        if t >= bot_info.max_tier - 1:
            msg += "\nT가 Max를 초과하여 손절합니다"
            trade_type, amount = self._calculate_sell_amount(False, True, bot_info)
        else:
            trade_type, amount = self._calculate_sell_amount(condition_3_4, condition_1_4, bot_info)

            # 적은 수익 매도 스킵 (100$ 이하)
            if trade_type and self._is_sell_skip(cur_price, avr_price, bot_info, profit_std=100):
                send_message_sync(msg + "‼️ 수익금이 100$ 이하라 매도를 스킵합니다")
                return None

        # 매도 실행
        if trade_type:
            return self._request_sell(bot_info, trade_type, amount, msg)
        else:
            send_message_sync(f"[{bot_info.name}] 판매 조건이 없습니다")
            return None

    def _execute_buy(self, bot_info: BotInfo) -> Optional[tuple[TradeType, float]]:
        """
        매수 조건 체크 및 실행

        Args:
            bot_info: 봇 정보

        Returns:
            Optional[tuple]: (TradeType, seed) 또는 None

        egg/trade_module.py의 buy() 이관 (116-172번 줄)
        """
        avr_price = self.trade_repo.get_average_purchase_price(bot_info.name)
        cur_price = self.hantoo_service.get_price(bot_info.symbol)
        if not cur_price:
            send_message_sync(f"[{bot_info.name}] 현재가 조회 실패")
            return None

        # 최대 투자금 체크
        if not self._is_buy_available_for_max_balance(bot_info):
            return None

        # 첫 구매 (평단가가 없으면)
        if not avr_price:
            send_message_sync(f"첫 구매 {bot_info.seed:,.0f}$ 매수 시도합니다")
            return self._request_buy(bot_info, TradeType.BUY, bot_info.seed)

        point_price, t, point = self._get_point_price(bot_info)

        # 활성화된 조건 개수 계산 (이동평균가 조건 제거)
        enabled_count = sum([
            bot_info.is_check_buy_avr_price,
            bot_info.is_check_buy_t_div_price
        ])

        # 조건 1: 평단가보다 낮은지 체크
        # 조건 2: %지점 보다 낮은지 체크
        condition_avr = cur_price < avr_price and bot_info.is_check_buy_avr_price
        condition_point = cur_price < point_price and bot_info.is_check_buy_t_div_price

        satisfied_count = sum([condition_avr, condition_point])

        # 조건이 하나도 없거나 만족하는 조건이 없으면 구매 불가
        if enabled_count == 0 or satisfied_count == 0:
            send_message_sync(f"[{bot_info.name}] 구매 조건이 없습니다")
            return None

        # 매수 비율 계산 (만족한 조건 수 / 활성화된 조건 수)
        buy_ratio = satisfied_count / enabled_count
        result_msg = f"{satisfied_count}/{enabled_count}개 만족하여 시드를 {buy_ratio * 100:,.0f}%만큼 조절합니다\n"

        avr_msg = f"- 평단가({avr_price:.2f})[{util.get_ox_emoji(condition_avr)}]\n" if bot_info.is_check_buy_avr_price else ""
        point_msg = f"- %지점가({point_price:.2f})[{util.get_ox_emoji(condition_point)}] ({point * 100:.2f}%)\n" if bot_info.is_check_buy_t_div_price else ""

        msg = (f"[구매검사({bot_info.name})]\n"
               f"현재 활성화된 조건 검사 개수는 {enabled_count}개 입니다\n\n"
               f"{avr_msg}{point_msg}"
               f"{result_msg}"
               f"현재 반복리 추가금은 {bot_info.added_seed:,.0f}$ 입니다\n\n")

        # T가 2/3 미만이면 큰 하락 체크
        if t < bot_info.max_tier * 2 / 3:
            adjust_seed = self._check_big_drop(bot_info, cur_price)
        else:
            adjust_seed = bot_info.seed + bot_info.added_seed

        seed = adjust_seed * buy_ratio if adjust_seed is not None else 0

        send_message_sync(msg)
        return self._request_buy(bot_info, TradeType.BUY, seed)

    def _calculate_sell_amount(
        self,
        condition_3_4: bool,
        condition_1_4: bool,
        bot_info: BotInfo
    ) -> Tuple[Optional[TradeType], int]:
        """
        매도 조건에 따른 매도 수량 및 타입 계산

        Args:
            condition_3_4: 익절가 돌파 여부
            condition_1_4: %지점가 돌파 여부
            bot_info: 봇 정보

        Returns:
            (매도 타입, 매도 수량) 튜플

        egg/trade_module.py의 re_make_sell_amount() 이관 (90-100번 줄)
        """
        total_amount = self.trade_repo.get_total_amount(bot_info.name)

        if condition_3_4 and condition_1_4:
            return TradeType.SELL, int(total_amount)  # 전체 매도
        elif condition_3_4:
            return TradeType.SELL_3_4, int(total_amount * 3 / 4)  # 3/4 매도
        elif condition_1_4:
            return TradeType.SELL_1_4, int(total_amount * 1 / 4)  # 1/4 매도

        return None, int(total_amount)

    def _is_sell_skip(
        self,
        cur_price: float,
        avr_price: float,
        bot_info: BotInfo,
        profit_std: float
    ) -> bool:
        """
        적은 수익 매도 스킵 여부 판단

        Args:
            cur_price: 현재가
            avr_price: 평단가
            bot_info: 봇 정보
            profit_std: 수익 기준 금액 (달러)

        Returns:
            True: 스킵해야 함, False: 스킵 안함

        egg/trade_module.py의 is_sell_skip() 이관 (84-87번 줄)
        """
        cur_trade = self.trade_repo.find_by_name(bot_info.name)
        if not cur_trade:
            return False

        profit = (cur_price - avr_price) * cur_trade.amount
        return 0 < profit < profit_std

    def _check_big_drop(self, bot_info: BotInfo, cur_price: float) -> Optional[float]:
        """
        큰 하락 시 시드 조정

        Args:
            bot_info: 봇 정보
            cur_price: 현재가

        Returns:
            조정된 시드 (잔고 부족 시 None)

        egg/trade_module.py의 check_big_drop() 이관 (175-222번 줄)
        """
        prev_price = self.hantoo_service.get_prev_price(bot_info.symbol)  # 전일 종가
        if not prev_price:
            send_message_sync(f"[{bot_info.name}] 전일 종가 조회 실패")
            return bot_info.seed + bot_info.added_seed

        origin_seed = bot_info.seed

        # 하락률 계산 (% 단위)
        drop_ratio = (prev_price - cur_price) / prev_price * 100

        # 상승 / 하락 알림
        if drop_ratio > 0:
            send_message_sync(f"[{bot_info.symbol}] 현재가 전일 대비 하락률: {drop_ratio:,.2f}%")
        else:
            send_message_sync(f"[{bot_info.symbol}] 현재가 전일 대비 상승률: {abs(drop_ratio):,.2f}%")

        # 종목별 민감도 설정
        ratio_step = 3 if bot_info.symbol == "TQQQ" else 5

        # 하락률 구간별 증액 비율 (큰 값부터 체크)
        if drop_ratio >= ratio_step * 3:
            seed = origin_seed * 1.50  # 큰 하락 → 50% 증액
        elif drop_ratio >= ratio_step * 2:
            seed = origin_seed * 1.40
        elif drop_ratio >= ratio_step * 1:
            seed = origin_seed * 1.30
        else:
            seed = origin_seed

        seed += bot_info.added_seed

        # 잔고 확인
        balance = self.hantoo_service.get_balance()
        if balance < seed:
            send_message_sync(
                f"⚠️ [{bot_info.symbol}] 시드 조정 실패 — 잔고 부족 (필요: {seed:,.2f}, 보유: {balance:,.2f})"
            )
            return None

        # seed 조정 알림
        if origin_seed + bot_info.added_seed != seed:
            # 증가율 계산 (원래 시드 대비 몇 % 증가했는지)
            increase_ratio = ((seed - origin_seed) / origin_seed) * 100

            send_message_sync(
                f"✅ [{bot_info.symbol}] 전일 대비 {drop_ratio:.2f}% 하락 → "
                f"seed 조정: {origin_seed:,.2f} → {seed:,.2f} "
                f"(+{increase_ratio:.1f}%)"
            )

        return seed

    def _request_buy(self, bot_info: BotInfo, trade_type: TradeType, seed: float) -> tuple[TradeType, float]:
        """
        매수 주문 정보 반환 (Job에서 OrderUsecase 호출용)

        Args:
            bot_info: 봇 정보
            trade_type: 거래 타입
            seed: 매수 금액 (달러)

        Returns:
            (거래 타입, 매수 금액)

        egg/trade_module.py의 request_buy() 이관 (225-230번 줄)
        """
        send_message_sync(f"[{bot_info.name}] 매수 판단: {seed:,.2f}$ ({trade_type.value})")
        return trade_type, seed

    def _request_sell(
        self,
        bot_info: BotInfo,
        trade_type: TradeType,
        amount: int,
        msg: str = ""
    ) -> tuple[TradeType, int]:
        """
        매도 주문 정보 반환 (Job에서 OrderUsecase 호출용)

        Args:
            bot_info: 봇 정보
            trade_type: 거래 타입
            amount: 매도 수량
            msg: 추가 메시지

        Returns:
            (거래 타입, 매도 수량)

        egg/trade_module.py의 request_sell() 이관 (233-234번 줄)
        """
        send_message_sync(msg + f"\n[{bot_info.name}] 매도 판단: {amount}주 ({trade_type.value})")
        return trade_type, amount

    def _is_buy_available_for_max_balance(self, bot_info: BotInfo) -> bool:
        """
        최대 투자금 체크

        Args:
            bot_info: 봇 정보

        Returns:
            True: 구매 가능, False: 구매 불가

        egg/trade_module.py의 is_buy_available_for_max_balance() 이관 (237-246번 줄)
        """
        max_balance = bot_info.seed * bot_info.max_tier
        total_investment = self.trade_repo.get_total_investment(bot_info.name)
        msg = (f"[투자금 체크]\n"
               f"현재투자금({total_investment:.2f}) <= 최대투자금({(max_balance - bot_info.seed):.2f})")
        print(msg)

        if total_investment > max_balance - bot_info.seed:
            msg += "\n투자금이 Max금액을 초과해 구매가 불가능합니다"
            send_message_sync(msg)
            return False

        return True

    def _get_point_price(self, bot_info: BotInfo) -> Tuple[Optional[float], float, float]:
        """
        %지점가, T, point 계산

        Args:
            bot_info: 봇 정보

        Returns:
            (point_price, t, point) 튜플
            - point_price: %지점가 (평단가 * (1 + point)), avr_price가 없으면 None
            - t: T 값 (총 투자금 / seed)
            - point: % 지점 (예: 0.05 = 5%)

        egg/trade_module.py의 get_point_price() 이관 (249-256번 줄)
        BotManagementUsecase._get_point_price()와 동일
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

    def _save_sell_to_db(self, bot_info: BotInfo, trade_result) -> None:
        """
        매도 DB 저장 + History (force_sell용)

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과

        OrderUsecase._save_sell_to_db()와 동일한 로직
        egg/db_usecase.py의 write_sell_db() 이관 (7-37번 줄)
        """
        from datetime import datetime

        is_update_added_seed = False
        if not trade_result:
            send_message_sync(f"[{bot_info.name}] 거래를 찾을 수 없어 종료합니다")
            return

        msg = (f"[거래완료] {bot_info.symbol}({trade_result.trade_type})\n"
               f"총판매금액 : {float(trade_result.total_price):.2f}$\n"
               f"판매단가 : {float(trade_result.unit_price):.2f}$\n"
               f"수량 : {float(trade_result.amount):.0f}개")
        send_message_sync(msg)

        prev_trade = self.trade_repo.find_by_name(bot_info.name)

        # 부분 매도인 경우 Trade 리밸런싱
        if trade_result.trade_type.is_partial_sell():
            new_trade = self.trade_repo.rebalance_trade(
                name=bot_info.name,
                symbol=bot_info.symbol,
                prev_trade=prev_trade,
                trade_result=trade_result
            )

            if new_trade.amount > 0:
                self.trade_repo.save(new_trade)
                is_update_added_seed = True
            else:
                self.trade_repo.delete_by_name(bot_info.name)
        else:
            # 전체 매도인 경우 Trade 삭제
            self.trade_repo.delete_by_name(bot_info.name)

        # History 저장
        self._save_history(bot_info, trade_result, prev_trade, is_update_added_seed)

    def _save_history(self, bot_info: BotInfo, trade_result, prev_trade, is_update_added_seed: bool) -> None:
        """
        History 저장 + added_seed 업데이트 (force_sell용)

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과
            prev_trade: 이전 거래 정보
            is_update_added_seed: added_seed 업데이트 여부

        OrderUsecase._save_history()와 동일한 로직
        egg/db_usecase.py의 write_history_db() 이관 (40-73번 줄)
        """
        from datetime import datetime
        from domain.entities.history import History

        profit = round(trade_result.total_price - prev_trade.purchase_price * trade_result.amount, 2)
        profit_rate = util.get_profit_rate(
            cur_price=trade_result.unit_price,
            purchase_price=prev_trade.purchase_price
        ) / 100

        emoji = "💰" if profit > 0 else "😭"
        send_message_sync(
            f"{emoji} [{bot_info.name}] 판매기록\n"
            f"손익금 : {profit}$"
        )

        # History 저장
        history = History(
            date_added=prev_trade.date_added,
            sell_date=datetime.now(),
            trade_type=trade_result.trade_type,
            name=bot_info.name,
            symbol=bot_info.symbol,
            buy_price=prev_trade.purchase_price,
            sell_price=trade_result.unit_price,
            profit=profit,
            profit_rate=profit_rate
        )
        self.history_repo.save(history)

        # added_seed 업데이트
        if is_update_added_seed:
            # 부분 매도 → added_seed에 수익금 추가
            bot_info.added_seed += profit
            self.bot_info_repo.save(bot_info)
        else:
            # 전체 매도 → added_seed 초기화 + 사이클 종료
            bot_info.added_seed = 0
            self.bot_info_repo.save(bot_info)
            self._finish_cycle(bot_info, prev_trade.date_added)

    def _finish_cycle(self, bot_info: BotInfo, date_added) -> None:
        """
        사이클 종료 메시지 (force_sell용)

        Args:
            bot_info: 봇 정보
            date_added: 사이클 시작 날짜

        OrderUsecase._finish_cycle()와 동일한 로직
        egg/db_usecase.py의 finish_cycle() 이관 (76-92번 줄)
        """
        try:
            total = self.history_repo.get_total_profit_by_name_and_date(bot_info.name, date_added)

            date_str = date_added.strftime(f'🎉축하합니다\n'
                                          f'%Y년 %m월 %d일 시작\n{bot_info.name} 사이클이 종료\n'
                                          f'최종수익금 💰{total:,.2f}$\n\n')

            history_list = self.history_repo.find_by_name_and_date(bot_info.name, date_added)
            msg = ""
            for history in history_list:
                date = history.sell_date.strftime('%Y년 %m월 %d일')
                msg += f"📆{date}\n -> {history.trade_type.name} : 💰{history.profit:,.2f}$\n"

            send_message_sync(date_str + msg)
        except Exception as e:
            send_message_sync(f"사이클종료 메시지에 에러가 생겼습니다. 거래와는 무관합니다 {e}")
