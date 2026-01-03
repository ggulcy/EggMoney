"""주문서 생성 Usecase - 매도/매수 조건 판단 및 주문서 생성/저장"""
from datetime import datetime
from typing import Optional, Tuple, List, Dict

from config import util
from config.item import get_drop_interval_rate
from config.key_store import read, TWAP_COUNT
from domain.entities.bot_info import BotInfo
from domain.entities.order import Order
from domain.repositories import (
    BotInfoRepository,
    TradeRepository,
    HistoryRepository,
    OrderRepository,
    ExchangeRepository,
    MessageRepository,
)
from domain.value_objects.order_type import OrderType
from domain.value_objects.trade_type import TradeType
from domain.value_objects.netting_pair import NettingPair


class OrderUsecase:
    """주문서 생성 Usecase

    egg/trade_module.py 이관
    - 매도/매수 조건 판단
    - 주문서 정보 생성 및 DB 저장
    """

    def __init__(
            self,
            bot_info_repo: BotInfoRepository,
            trade_repo: TradeRepository,
            history_repo: HistoryRepository,
            order_repo: OrderRepository,
            exchange_repo: ExchangeRepository,
            message_repo: MessageRepository
    ):
        """
        주문서 생성 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            history_repo: History 리포지토리 (오늘 매도 이력 확인)
            order_repo: Order 리포지토리 (오늘 매도 주문 확인)
            exchange_repo: 증권사 API 리포지토리
            message_repo: 메시지 발송 리포지토리
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.history_repo = history_repo
        self.order_repo = order_repo
        self.exchange_repo = exchange_repo
        self.message_repo = message_repo

    # ===== Public Methods (Router/Scheduler에서 호출) =====

    def save_buy_order(self, bot_info: BotInfo, seed: float, trade_type: TradeType) -> None:
        """
        매수 주문서 DB 저장

        Args:
            bot_info: 봇 정보
            seed: 매수 금액 (달러)
            trade_type: 거래 타입

        egg/order_module.py의 make_buy_order_list() 이관 (43-69번 줄)
        """
        try:
            twap_count = read(TWAP_COUNT)
            if not twap_count:
                twap_count = 5  # 기본값

            order = Order(
                date_added=datetime.now(),
                name=bot_info.name,
                symbol=bot_info.symbol,
                trade_result_list=[],
                order_type=OrderType(trade_type.value),
                trade_count=twap_count,
                total_count=twap_count,
                remain_value=seed,
                total_value=seed
            )

            self.order_repo.save(order)

            self.message_repo.send_message(f"{order.name} 구매 요청에 대한 주문 리스트를 생성하였습니다\n"
                              f"분할 회수 : {order.trade_count}\n"
                              f"총 구매 금액 : {order.remain_value:,.2f}$")

        except ValueError as e:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 구매 주문서를 생성할 수 없습니다.\n"
                              f"이유: 기존 주문서에 미체결 주문(odno_list)이 남아있습니다.\n"
                              f"상세: {str(e)}")

    def save_sell_order(self, bot_info: BotInfo, amount: int, trade_type: TradeType) -> None:
        """
        매도 주문서 DB 저장

        Args:
            bot_info: 봇 정보
            amount: 매도 수량
            trade_type: 거래 타입

        egg/order_module.py의 make_sell_order_list() 이관 (14-40번 줄)
        """
        try:
            twap_count = read(TWAP_COUNT)
            if not twap_count:
                twap_count = 5  # 기본값

            order = Order(
                date_added=datetime.now(),
                name=bot_info.name,
                symbol=bot_info.symbol,
                trade_result_list=[],
                order_type=OrderType(trade_type.value),
                trade_count=twap_count,
                total_count=twap_count,
                remain_value=amount,
                total_value=amount
            )

            self.order_repo.save(order)

            self.message_repo.send_message(f"{order.name} 판매 요청에 대한 주문 리스트를 생성하였습니다\n"
                              f"분할 회수 : {order.trade_count}\n"
                              f"총 판매 개수 : {order.remain_value}")

        except ValueError as e:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 판매 주문서를 생성할 수 없습니다.\n"
                              f"이유: 기존 주문서에 미체결 주문(odno_list)이 남아있습니다.\n"
                              f"상세: {str(e)}")

    def create_order(self, bot_info: BotInfo) -> Optional[tuple]:
        """
        주문서 생성 (매도 → 매수 순차 검사)

        Args:
            bot_info: 봇 정보

        Returns:
            Optional[tuple]: (TradeType, value) - 매도는 (type, amount), 매수는 (type, seed)
                           조건 불충족 시 None

        egg/trade_module.py의 trade() 이관 (25-34번 줄)
        """
        # 1. 매도 주문서 생성 (skip_sell이 False일 때만)
        if not bot_info.skip_sell:
            result = self._create_sell_order(bot_info)
            if result:
                return result

        # 2. 매도가 일어난 날(또는 매도 예정인 날)은 구매하지 않음
        if self.history_repo.find_today_sell_by_name(bot_info.name) or \
                self.order_repo.has_sell_order_today(bot_info.name):
            return None

        # 3. 매수 주문서 생성
        return self._create_buy_order(bot_info)

    # ===== Private Methods (내부 헬퍼) =====

    def _create_sell_order(self, bot_info: BotInfo) -> Optional[tuple[TradeType, int]]:
        """
        매도 주문서 생성 (조건 체크 + 주문 정보 반환)

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
        cur_price = self.exchange_repo.get_price(bot_info.symbol)
        if not cur_price:
            self.message_repo.send_message(f"[{bot_info.name}] 현재가 조회 실패")
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

        # 매도 주문 정보 반환
        if trade_type:
            self.message_repo.send_message(msg + f"\n[{bot_info.name}] 매도 주문서 생성: {amount}주 ({trade_type.value})")
            return trade_type, amount
        else:
            self.message_repo.send_message(f"[{bot_info.name}] 판매 조건이 없습니다")
            return None

    def _create_buy_order(self, bot_info: BotInfo) -> Optional[tuple[TradeType, float]]:
        """
        매수 주문서 생성 (조건 체크 + 주문 정보 반환)

        Args:
            bot_info: 봇 정보

        Returns:
            Optional[tuple]: (TradeType, seed) 또는 None

        egg/trade_module.py의 buy() 이관 (116-172번 줄)
        """
        avr_price = self.trade_repo.get_average_purchase_price(bot_info.name)
        cur_price = self.exchange_repo.get_price(bot_info.symbol)
        if not cur_price:
            self.message_repo.send_message(f"[{bot_info.name}] 현재가 조회 실패")
            return None

        # 최대 투자금 체크
        if not self._is_buy_available_for_max_balance(bot_info):
            self.message_repo.send_message(f"[{bot_info.name}] 최대투자금을 초과하여 주문서를 생성하지 않습니다")
            return None

        # 첫 구매 (평단가가 없으면)
        if not avr_price or bot_info.skip_sell:
            self.message_repo.send_message(f"[첫 구매 or 판매스킵] 모든시드 {bot_info.seed:,.0f}$ 매수 시도합니다")
            return TradeType.BUY, bot_info.seed

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
            self.message_repo.send_message(f"[{bot_info.name}] 구매 조건이 없습니다")
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

        self.message_repo.send_message(msg)
        return TradeType.BUY, seed

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

        # 다이나믹 시드가 동작 가능한 경우 빅드랍 체크는 패스
        if bot_info.seed != bot_info.dynamic_seed_max:
            return bot_info.seed + bot_info.added_seed

        prev_price = self.exchange_repo.get_prev_price(bot_info.symbol)  # 전일 종가
        if not prev_price:
            self.message_repo.send_message(f"[{bot_info.name}] 전일 종가 조회 실패")
            return bot_info.seed + bot_info.added_seed

        origin_seed = bot_info.seed

        # 하락률 계산 (% 단위)
        drop_ratio = (prev_price - cur_price) / prev_price * 100

        # 상승 / 하락 알림
        if drop_ratio > 0:
            self.message_repo.send_message(f"[{bot_info.symbol}] 현재가 전일 대비 하락률: {drop_ratio:,.2f}%")
        else:
            self.message_repo.send_message(f"[{bot_info.symbol}] 현재가 전일 대비 상승률: {abs(drop_ratio):,.2f}%")

        # 종목별 민감도 설정
        ratio_step = get_drop_interval_rate(bot_info.symbol) * 100

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
        balance = self.exchange_repo.get_balance()
        if balance < seed:
            self.message_repo.send_message(
                f"⚠️ [{bot_info.symbol}] 시드 조정 실패 — 잔고 부족 (필요: {seed:,.2f}, 보유: {balance:,.2f})"
            )
            return None

        # seed 조정 알림
        if origin_seed + bot_info.added_seed != seed:
            # 증가율 계산 (원래 시드 대비 몇 % 증가했는지)
            increase_ratio = ((seed - origin_seed) / origin_seed) * 100

            self.message_repo.send_message(
                f"✅ [{bot_info.symbol}] 전일 대비 {drop_ratio:.2f}% 하락 → "
                f"seed 조정: {origin_seed:,.2f} → {seed:,.2f} "
                f"(+{increase_ratio:.1f}%)"
            )

        return seed

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
            self.message_repo.send_message(msg)
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

    # ===== Netting (장부거래) Methods =====

    def find_netting_orders(self) -> List[NettingPair]:
        """
        같은 symbol의 Buy/Sell Order 쌍 탐색 (Greedy 1:1 매칭)

        알고리즘:
        1. 모든 Order를 symbol별로 그룹핑
        2. 같은 symbol에 Buy와 Sell이 둘 다 있으면:
           - 반복: 상쇄 가능한 쌍이 없을 때까지
             - 모든 (Buy, Sell) 쌍 중 가장 많이 상쇄되는 쌍 선택
             - NettingPair 리스트에 추가
             - 해당 Order의 remain_value 임시 차감
        3. 현재가 조회하여 NettingPair에 포함

        Returns:
            List[NettingPair]: 상쇄할 (buy, sell, amount, price) 쌍 리스트
        """
        orders = self.order_repo.find_all()

        if not orders:
            return []

        # 1. symbol별 그룹핑
        symbol_groups: Dict[str, Dict[str, List[Order]]] = {}
        for order in orders:
            if order.symbol not in symbol_groups:
                symbol_groups[order.symbol] = {'buy': [], 'sell': []}

            if order.is_buy_order():
                symbol_groups[order.symbol]['buy'].append(order)
            elif order.is_sell_order():
                symbol_groups[order.symbol]['sell'].append(order)

        netting_pairs = []

        # 2. 각 symbol에 대해 상쇄 쌍 찾기
        for symbol, groups in symbol_groups.items():
            buy_orders = groups['buy']
            sell_orders = groups['sell']

            # Buy와 Sell 둘 다 있어야 상쇄 가능
            if not buy_orders or not sell_orders:
                continue

            # 현재가 조회 (symbol당 한 번만)
            current_price = self.exchange_repo.get_price(symbol)
            if not current_price:
                self.message_repo.send_message(f"⚠️ [{symbol}] 장부거래 현재가 조회 실패")
                continue

            # 임시 remain_value 추적 (실제 Order 수정 없이 계산용)
            # 매수: 금액 → 수량으로 변환
            buy_remains = {
                o.name: self._get_buy_amount_from_seed(o.remain_value, current_price)
                for o in buy_orders
            }
            # 매도: 수량 그대로
            sell_remains = {o.name: int(o.remain_value) for o in sell_orders}

            # 3. Greedy 반복: 가장 많이 상쇄되는 쌍 선택
            while True:
                best_pair = None
                best_amount = 0

                for buy in buy_orders:
                    for sell in sell_orders:
                        buy_amt = buy_remains.get(buy.name, 0)
                        sell_amt = sell_remains.get(sell.name, 0)

                        if buy_amt <= 0 or sell_amt <= 0:
                            continue

                        netting_amt = min(buy_amt, sell_amt)
                        if netting_amt > best_amount:
                            best_amount = netting_amt
                            best_pair = (buy, sell)

                # 더 이상 상쇄 가능한 쌍 없음
                if best_pair is None or best_amount <= 0:
                    break

                buy, sell = best_pair

                # NettingPair 생성
                netting_pairs.append(NettingPair(
                    buy_order=buy,
                    sell_order=sell,
                    netting_amount=best_amount,
                    current_price=current_price
                ))

                # 임시 remain 차감 (다음 반복에서 고려)
                buy_remains[buy.name] -= best_amount
                sell_remains[sell.name] -= best_amount

        return netting_pairs

    def _get_buy_amount_from_seed(self, seed: float, current_price: float) -> int:
        """매수 금액(seed)을 수량으로 변환"""
        if current_price <= 0:
            return 0
        return int(seed / current_price)

    def update_order_after_netting(
        self,
        order: Order,
        netted_amount: int,
        current_price: float
    ) -> None:
        """
        장부거래 후 Order 업데이트

        Args:
            order: 업데이트할 주문서
            netted_amount: 상쇄된 수량 (개)
            current_price: 상쇄 시 사용된 현재가

        Note:
            - 매수 Order: remain_value는 금액($) → 금액 차감
            - 매도 Order: remain_value는 수량(개) → 수량 차감
        """
        if order.is_buy_order():
            # 매수: 금액 차감 (수량 × 단가)
            deducted_value = netted_amount * current_price
            order.remain_value -= deducted_value

            self.message_repo.send_message(
                f"📝 [{order.name}] 매수 주문서 장부거래 반영\n"
                f"  - 상쇄 수량: {netted_amount}개\n"
                f"  - 차감 금액: ${deducted_value:,.2f}\n"
                f"  - 남은 금액: ${order.remain_value:,.2f}"
            )
        else:
            # 매도: 수량 차감
            order.remain_value -= netted_amount

            self.message_repo.send_message(
                f"📝 [{order.name}] 매도 주문서 장부거래 반영\n"
                f"  - 상쇄 수량: {netted_amount}개\n"
                f"  - 남은 수량: {int(order.remain_value)}개"
            )

        # Order 저장 또는 삭제
        if order.remain_value <= 0:
            self.order_repo.delete_by_name(order.name)
            self.message_repo.send_message(f"🗑️ [{order.name}] 주문서 전량 상쇄 → 삭제 완료")
        else:
            self.order_repo.save(order)
