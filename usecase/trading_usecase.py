"""거래 실행 Usecase - TWAP 주문 실행 + DB 저장"""
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import util, item
from domain.entities.bot_info import BotInfo
from domain.entities.order import Order
from domain.entities.trade import Trade
from domain.repositories import (
    BotInfoRepository,
    TradeRepository,
    HistoryRepository,
    OrderRepository,
    ExchangeRepository,
    MessageRepository,
)
from domain.value_objects.order_type import OrderType
from domain.value_objects.trade_result import TradeResult
from domain.value_objects.trade_type import TradeType
from domain.value_objects.netting_pair import NettingPair


class TradingUsecase:
    """거래 실행 Usecase

    egg/order_module.py + egg/db_usecase.py 이관
    - TWAP 주문 실행
    - DB 저장 (Trade, History, BotInfo.added_seed)
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
        거래 실행 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            history_repo: History 리포지토리
            order_repo: Order 리포지토리
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
        from domain.value_objects.trade_type import TradeType
        from domain.value_objects.trade_result import TradeResult

        # 1. 조건 판단
        total_amount = self.trade_repo.get_total_amount(bot_info.name)
        sell_amount = int(total_amount * (sell_ratio / 100))
        trade_type = TradeType.SELL if sell_ratio == 100 else TradeType.SELL_PART

        if sell_amount == 0:
            self.message_repo.send_message(f"[{bot_info.name}] 판매할 거래가 존재하지 않습니다")
            return

        self.message_repo.send_message(f"[{bot_info.name}] 강제 매도 즉시 실행: {sell_amount}주 ({sell_ratio}%)")

        # 2. 현재가 조회
        request_price = self.exchange_repo.get_available_sell(bot_info.symbol)
        if not request_price:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 현재가 조회 실패")
            return

        # 3. 매도 실행
        trade_result = self.exchange_repo.sell(
            symbol=bot_info.symbol,
            amount=sell_amount,
            request_price=request_price
        )

        # 4. 거래 결과 확인 및 DB 저장
        if trade_result:
            # trade_type을 강제로 설정 (HantooService가 항상 SELL을 반환하므로)
            trade_result = TradeResult(
                trade_type=trade_type,
                amount=trade_result.amount,
                unit_price=trade_result.unit_price,
                total_price=trade_result.total_price
            )
            self.message_repo.send_message(f"✅ 강제 매도 체결\n"
                                           f"  - 거래유형: {trade_result.trade_type.value}\n"
                                           f"  - 체결개수: {trade_result.amount}\n"
                                           f"  - 체결가: ${trade_result.unit_price:,.2f}\n"
                                           f"  - 총액: ${trade_result.total_price:,.2f}")

            # DB 저장
            self._save_sell_to_db(bot_info, trade_result)
        else:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 강제 매도 실패")

    def execute_closing_buy(self, bot_info: BotInfo, seed: float) -> None:
        """
        장마감 급락 매수 실행 (TWAP 완료 후 별도 실행)

        Order 없이 직접 매수 API 호출 후 Trade/History DB에 저장합니다.

        Args:
            bot_info: 봇 정보
            seed: 매수 시드 금액 (달러)
        """
        request_price = self.exchange_repo.get_available_buy(bot_info.symbol)
        if not request_price:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 장마감 급락 매수: 현재가 조회 실패")
            return

        request_amount = util.get_buy_amount(seed, request_price)
        if request_amount <= 0:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 장마감 급락 매수: 매수 가능 수량 0")
            return

        trade_result = self.exchange_repo.buy(
            symbol=bot_info.symbol,
            amount=request_amount,
            request_price=request_price
        )

        if not trade_result:
            self.message_repo.send_message(f"❌ [{bot_info.name}] 장마감 급락 매수: 주문 실패")
            return

        trade_result.trade_type = TradeType.BUY
        self.message_repo.send_message(
            f"✅ [{bot_info.name}] 장마감 급락 매수 완료\n"
            f"  - 체결 수량: {trade_result.amount}\n"
            f"  - 체결 단가: ${trade_result.unit_price:,.2f}\n"
            f"  - 총 거래금액: ${trade_result.total_price:,.2f}"
        )
        self._save_buy_to_db(bot_info, trade_result)

    def execute_twap(self, bot_info: BotInfo) -> None:
        """
        TWAP 주문 실행 (1회)

        Args:
            bot_info: 봇 정보

        egg/order_module.py의 check_order_request() 이관 (97-115번 줄)
        """
        order = self.order_repo.find_by_name(bot_info.name)
        if not order:
            return

        current_num = order.total_count - order.trade_count + 1
        print(f"{order.name}의 {current_num}/{order.total_count} 주문검사를 시작합니다")

        if self._is_order_available(order):
            try:
                if self._is_buy(order):
                    order = self._execute_single_buy(order)
                else:
                    order = self._execute_single_sell(order)
                self.order_repo.save(order)
            except Exception as e:
                self.message_repo.send_message(
                    f"⚠️ [{order.name}] TWAP {current_num}/{order.total_count} 실행 중 오류 발생: {e}\n"
                    f"  → 다음 TWAP 시간에 계속 진행합니다"
                )
                # 예외 발생 시에도 order는 이미 업데이트된 상태 (None이 추가되고 trade_count 감소)

            # 주문 완료 시 DB 저장
            # 조건 1: trade_count가 0
            # 조건 2: 마지막 TWAP 시간이 지났고 유효한 거래가 있는 경우
            if order.trade_count == 0 or self._is_last_twap_passed(order):
                self._complete_trade(order)

    def execute_netting(self, netting_pair: NettingPair) -> None:
        """
        장부거래 실행 (API 호출 없이 내부 정산)

        Args:
            netting_pair: 상쇄할 Buy/Sell Order 쌍 + 수량 + 현재가

        처리 내용:
        1. 매수측 TradeResult 생성 → _save_buy_to_db() 호출
        2. 매도측 TradeResult 생성 → _save_sell_to_db() 호출
        3. 텔레그램 메시지 발송

        Note:
            Order 업데이트는 OrderUsecase.update_order_after_netting()에서 처리
        """
        buy_order = netting_pair.buy_order
        sell_order = netting_pair.sell_order
        amount = netting_pair.netting_amount
        price = netting_pair.current_price

        # 봇 정보 조회
        buy_bot_info = self.bot_info_repo.find_by_name(buy_order.name)
        sell_bot_info = self.bot_info_repo.find_by_name(sell_order.name)

        if not buy_bot_info or not sell_bot_info:
            self.message_repo.send_message(
                f"⚠️ 장부거래 실패: 봇 정보 조회 실패\n"
                f"  - 매수봇: {buy_order.name}\n"
                f"  - 매도봇: {sell_order.name}"
            )
            return

        # 장부거래 시작 메시지
        self.message_repo.send_message(
            f"🔄 [{buy_order.symbol}] 장부거래 시작\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 매수: {buy_order.name} +{amount}개\n"
            f"📉 매도: {sell_order.name} -{amount}개\n"
            f"💰 단가: ${price:,.2f}\n"
            f"💵 총액: ${amount * price:,.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

        # 1. 매수측 TradeResult 생성 및 DB 저장
        buy_trade_result = TradeResult(
            trade_type=TradeType(buy_order.order_type.value),  # BUY or BUY_FORCE
            amount=amount,
            unit_price=price,
            total_price=round(amount * price, 2)
        )
        self._save_buy_to_db(buy_bot_info, buy_trade_result)

        # 2. 매도측 TradeResult 생성 및 DB 저장
        # 원래 order_type에 따라 trade_type 결정:
        # - 부분 매도(SELL_1_4, SELL_3_4, SELL_PART): 원래 order_type 유지 → Trade 리밸런싱
        # - 전체 매도(SELL): 주문서 소진 여부에 따라 결정
        #   - 전량 소진 → SELL → Trade 삭제
        #   - 부분 소진 → SELL_PART → Trade 리밸런싱
        if sell_order.order_type.is_partial_sell():
            sell_trade_type = TradeType(sell_order.order_type.value)
        else:
            is_full_sell = sell_order.remain_value - amount <= 0
            sell_trade_type = TradeType.SELL if is_full_sell else TradeType.SELL_PART

        sell_trade_result = TradeResult(
            trade_type=sell_trade_type,
            amount=amount,
            unit_price=price,
            total_price=round(amount * price, 2)
        )
        self._save_sell_to_db(sell_bot_info, sell_trade_result)

        self.message_repo.send_message(
            f"✅ [{buy_order.symbol}] 장부거래 완료\n"
            f"  - {buy_order.name}: Trade/History 저장 완료\n"
            f"  - {sell_order.name}: Trade/History 저장 완료"
        )

    def estimate_capital_gains_tax_fee(self, name: str) -> Optional[Dict[str, Any]]:
        """
        양도세처리 예상 수수료 조회

        Args:
            name: Trade 이름

        Returns:
            {
                'amount': 보유 수량,
                'symbol': 심볼,
                'current_price': 현재가,
                'total_value': 총 거래금액 (매도+매수),
                'estimated_fee': 예상 수수료 (0.09%)
            }
        """
        # 1. Trade 조회
        trade = self.trade_repo.find_by_name(name)
        if not trade:
            return None

        amount = int(trade.amount)
        symbol = trade.symbol

        if amount <= 0:
            return None

        # 2. 현재가 조회
        current_price = self.exchange_repo.get_price(symbol)
        if not current_price:
            return None

        # 3. 예상 수수료 계산
        # 총 거래금액 = 현재가 × 수량 × 2 (매도 + 매수)
        total_value = current_price * amount * 2
        estimated_fee = total_value * 0.0009  # 0.09%

        # 4. 환율 조회
        usd_krw = util.get_naver_exchange_rate()

        return {
            'amount': amount,
            'symbol': symbol,
            'current_price': current_price,
            'total_value': round(total_value, 2),
            'estimated_fee': round(estimated_fee, 2),
            'usd_krw': usd_krw,
            'estimated_fee_krw': round(estimated_fee * usd_krw, 0)
        }

    def execute_capital_gains_tax_wash(self, name: str) -> Optional[Dict[str, Any]]:
        """
        양도세처리 실행 (30개 단위 매도 후 매수)

        DB 저장 없이 실제 거래만 실행

        Args:
            name: Trade 이름

        Returns:
            {
                'amount': 처리 수량,
                'symbol': 심볼,
                'sell_results': 매도 결과 리스트,
                'buy_results': 매수 결과 리스트,
                'total_sell_value': 총 매도 금액,
                'total_buy_value': 총 매수 금액,
                'actual_fee': 실제 수수료
            }
        """
        BATCH_SIZE = 30
        FEE_RATE = 0.0009  # 0.09%
        INTERVAL_SECONDS = 5

        # 1. Trade 조회
        trade = self.trade_repo.find_by_name(name)
        if not trade:
            self.message_repo.send_message(f"❌ [{name}] Trade를 찾을 수 없습니다")
            return None

        amount = int(trade.amount)
        symbol = trade.symbol

        if amount <= 0:
            self.message_repo.send_message(f"❌ [{name}] 보유 수량이 없습니다")
            return None

        # 2. 배치 분할 (30개 단위)
        batches = []
        remaining = amount
        while remaining > 0:
            batch_size = min(BATCH_SIZE, remaining)
            batches.append(batch_size)
            remaining -= batch_size

        self.message_repo.send_message(
            f"📋 [{name}] 양도세처리 시작\n"
            f"  - 심볼: {symbol}\n"
            f"  - 총 수량: {amount}개\n"
            f"  - 배치: {batches}"
        )

        # 3. 매도 실행
        sell_results = []
        for i, batch_amount in enumerate(batches):
            # 첫 번째 거래가 아니면 5초 대기 (테스트 모드에서는 스킵)
            if i > 0 and not item.is_test:
                time.sleep(INTERVAL_SECONDS)

            request_price = self.exchange_repo.get_available_sell(symbol)

            if not request_price:
                self.message_repo.send_message(f"❌ [{name}] 매도 {i + 1}/{len(batches)} 현재가 조회 실패")
                continue

            result = self.exchange_repo.sell(
                symbol=symbol,
                amount=batch_amount,
                request_price=request_price
            )

            if result:
                sell_results.append({
                    'amount': result.amount,
                    'unit_price': result.unit_price,
                    'total_price': result.total_price
                })
                self.message_repo.send_message(
                    f"📉 [{name}] 매도 {i + 1}/{len(batches)} 완료: "
                    f"{result.amount}개 × ${result.unit_price:,.2f} = ${result.total_price:,.2f}"
                )
            else:
                self.message_repo.send_message(f"❌ [{name}] 매도 {i + 1}/{len(batches)} 실패")

        # 4. 매수 실행
        buy_results = []
        for i, batch_amount in enumerate(batches):
            # 매 거래마다 3초 대기 (테스트 모드에서는 스킵)
            if not item.is_test:
                time.sleep(INTERVAL_SECONDS)

            request_price = self.exchange_repo.get_available_buy(symbol)
            if not request_price:
                self.message_repo.send_message(f"❌ [{name}] 매수 {i + 1}/{len(batches)} 현재가 조회 실패")
                continue

            result = self.exchange_repo.buy(
                symbol=symbol,
                amount=batch_amount,
                request_price=request_price
            )

            if result:
                buy_results.append({
                    'amount': result.amount,
                    'unit_price': result.unit_price,
                    'total_price': result.total_price
                })
                self.message_repo.send_message(
                    f"📈 [{name}] 매수 {i + 1}/{len(batches)} 완료: "
                    f"{result.amount}개 × ${result.unit_price:,.2f} = ${result.total_price:,.2f}"
                )
            else:
                self.message_repo.send_message(f"❌ [{name}] 매수 {i + 1}/{len(batches)} 실패")

        # 5. 결과 집계
        total_sell_value = sum(r['total_price'] for r in sell_results)
        total_buy_value = sum(r['total_price'] for r in buy_results)
        total_value = total_sell_value + total_buy_value
        actual_fee = total_value * FEE_RATE
        spread_cost = total_buy_value - total_sell_value
        total_cost = spread_cost + actual_fee

        # 환율 조회
        usd_krw = util.get_naver_exchange_rate()

        self.message_repo.send_message(
            f"✅ [{name}] 양도세처리 완료\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 총 매도: ${total_sell_value:,.2f}\n"
            f"📈 총 매수: ${total_buy_value:,.2f}\n"
            f"💸 스프레드: ${spread_cost:,.2f}\n"
            f"💰 수수료: ${actual_fee:,.2f} (0.09%)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 총 비용: ${total_cost:,.2f} (₩{total_cost * usd_krw:,.0f})"
        )

        return {
            'amount': amount,
            'symbol': symbol,
            'sell_results': sell_results,
            'buy_results': buy_results,
            'total_sell_value': round(total_sell_value, 2),
            'total_buy_value': round(total_buy_value, 2),
            'actual_fee': round(actual_fee, 2),
            'usd_krw': usd_krw,
            'spread_cost': round(spread_cost, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_krw': round(total_cost * usd_krw, 0)
        }

    # ===== Private Methods (내부 헬퍼) =====

    def _is_last_twap_passed(self, order: Order) -> bool:
        """
        마지막 TWAP 시간이 지났는지 확인

        Args:
            order: 주문 정보

        Returns:
            True: 마지막 TWAP 시간이 지났고 유효한 거래가 있음
            False: 아직 마지막 TWAP 시간 전이거나 유효한 거래가 없음
        """
        from config.util import get_schedule_times

        try:
            # 유효한 거래 결과 확인
            valid_results = [tr for tr in order.trade_result_list if tr is not None]
            if not valid_results:
                return False

            # 스케줄 시간 조회
            _, _, twap_times, _ = get_schedule_times()
            if not twap_times:
                return False

            # 마지막 TWAP 시간 (예: "04:50")
            last_time_str = twap_times[-1]

            # 현재 시간
            now = datetime.now()

            # 오늘 날짜 + 마지막 TWAP 시간
            today = now.date()
            last_twap_time = datetime.strptime(f"{today} {last_time_str}", "%Y-%m-%d %H:%M")

            # 현재 시간이 마지막 TWAP 시간 이후인지 확인
            if now >= last_twap_time:
                self.message_repo.send_message(
                    f"⏰ [{order.name}] 마지막 TWAP 시간({last_time_str}) 경과\n"
                    f"  → 완료된 거래: {len(valid_results)}/{order.total_count}\n"
                    f"  → 거래 종료 처리를 시작합니다"
                )
                return True

            return False

        except Exception as e:
            # 예외 발생 시 기존 로직대로 trade_count == 0만 체크
            print(f"⚠️ 마지막 TWAP 시간 체크 실패: {e}")
            return False

    def _is_order_available(self, order: Order) -> bool:
        """
        주문 가능 여부 체크

        Args:
            order: 주문 정보

        Returns:
            True: 주문 가능, False: 주문 불가

        egg/order_module.py의 is_order_available() 이관 (72-94번 줄)
        """
        # 1. 오늘 날짜 확인
        today = datetime.now().date()
        order_date = order.date_added.date()

        if order_date != today:
            self.message_repo.send_message(f"⚠️ [{order.name}] 주문 날짜가 오늘이 아닙니다. (주문 날짜: {order_date}, 오늘: {today})")
            return False

        # 2. 거래결과 개수 확인
        current_result_count = len(order.trade_result_list) if order.trade_result_list else 0

        if current_result_count >= order.total_count:
            self.message_repo.send_message(
                f"⚠️ [{order.name}] 이미 모든 거래가 완료되었습니다. ({current_result_count}/{order.total_count})")
            return False

        # 3. trade_count 확인
        if order.trade_count <= 0:
            self.message_repo.send_message(f"⚠️ [{order.name}] 남은 거래 횟수가 없습니다. (trade_count: {order.trade_count})")
            return False

        return True

    def _is_buy(self, order: Order) -> bool:
        """
        매수 주문인지 확인

        Args:
            order: 주문 정보

        Returns:
            True: 매수, False: 매도

        egg/order_module.py의 is_buy() 이관 (118-119번 줄)
        """
        return order.order_type in [OrderType.BUY, OrderType.BUY_FORCE]

    def _execute_single_buy(self, order: Order) -> Order:
        """
        개별 매수 실행

        Args:
            order: 주문 정보

        Returns:
            업데이트된 주문 정보

        egg/order_module.py의 request_buy_order() 이관 (122-173번 줄)
        """
        if order.trade_count == 0:
            self.message_repo.send_message("거래가능한 주문이 없습니다")
            return order

        # 주문 요청 정보 계산
        request_price = self.exchange_repo.get_available_buy(order.symbol)
        if not request_price:
            self.message_repo.send_message(f"❌ [{order.name}] 현재가 조회 실패")
            order.trade_result_list.append(None)
            order.trade_count -= 1
            return order

        request_seed = int(order.remain_value * (1 / order.trade_count))
        request_amount = util.get_buy_amount(request_seed, request_price)

        # 요청 정보 출력
        print(f"[{order.name}] 구매 주문을 요청합니다\n"
              f"  📊 요청 정보:\n"
              f"    - 이름: {order.name}\n"
              f"    - 심볼: {order.symbol}\n"
              f"    - 수량: {request_amount}\n"
              f"    - 총액: ${request_seed:,.0f}")

        # 주문 실행
        trade_result = self.exchange_repo.buy(
            symbol=order.symbol,
            amount=request_amount,
            request_price=request_price
        )

        if order.trade_result_list is None:
            order.trade_result_list = []

        # 거래 결과 저장
        if trade_result:
            trade_result.trade_type = TradeType(order.order_type.value)
            trade_result_dict = {
                'trade_type': trade_result.trade_type.value,
                'amount': trade_result.amount,
                'unit_price': trade_result.unit_price,
                'total_price': trade_result.total_price
            }
            order.trade_result_list.append(trade_result_dict)
            order.remain_value -= trade_result.total_price
        else:
            order.trade_result_list.append(None)

        # 현재 거래 횟수 계산
        current_trade_num = order.total_count - order.trade_count + 1
        order.trade_count -= 1

        # 결과 출력
        if trade_result:
            print(f"✅ [{order.name}] 개별 거래 결과 ({current_trade_num}/{order.total_count})\n"
                  f"  - 거래유형: {trade_result.trade_type.value}\n"
                  f"  - 체결개수: {trade_result.amount}\n"
                  f"  - 체결가: ${trade_result.unit_price:,.2f}")
        else:
            print(f"✅ [{order.name}] 거래 결과: 거래 실패 or 거래가 없습니다 ({current_trade_num}/{order.total_count})")

        return order

    def _execute_single_sell(self, order: Order) -> Order:
        """
        개별 매도 실행

        Args:
            order: 주문 정보

        Returns:
            업데이트된 주문 정보

        egg/order_module.py의 request_sell_order() 이관 (176-225번 줄)
        """
        if order.trade_count == 0:
            self.message_repo.send_message("거래가능한 주문이 없습니다")
            return order

        # 주문 요청 정보 계산
        request_amount = int(order.remain_value * (1 / order.trade_count))

        # 요청 정보 출력
        print(f"[{order.name}] 판매 주문을 요청합니다\n"
              f"  📊 요청 정보:\n"
              f"    - 이름: {order.name}\n"
              f"    - 심볼: {order.symbol}\n"
              f"    - 수량: {request_amount}")

        # 주문 실행
        request_price = self.exchange_repo.get_available_sell(order.symbol)
        if not request_price:
            self.message_repo.send_message(f"❌ [{order.name}] 현재가 조회 실패")
            order.trade_result_list.append(None)
            order.trade_count -= 1
            return order

        trade_result = self.exchange_repo.sell(
            symbol=order.symbol,
            amount=request_amount,
            request_price=request_price
        )

        if order.trade_result_list is None:
            order.trade_result_list = []

        # 거래 결과 저장
        if trade_result:
            trade_result.trade_type = TradeType(order.order_type.value)
            trade_result_dict = {
                'trade_type': trade_result.trade_type.value,
                'amount': trade_result.amount,
                'unit_price': trade_result.unit_price,
                'total_price': trade_result.total_price
            }
            order.trade_result_list.append(trade_result_dict)
            order.remain_value -= trade_result.amount  # 판매는 수량을 차감
        else:
            order.trade_result_list.append(None)

        # 현재 거래 횟수 계산
        current_trade_num = order.total_count - order.trade_count + 1
        order.trade_count -= 1

        # 결과 출력
        if trade_result:
            print(f"✅ [{order.name}] 개별 거래 결과 ({current_trade_num}/{order.total_count})\n"
                  f"  - 거래유형: {trade_result.trade_type.value}\n"
                  f"  - 체결개수: {trade_result.amount}\n"
                  f"  - 체결가: ${trade_result.unit_price:,.2f}")
        else:
            print(f"✅ [{order.name}] 거래 결과: 거래 실패 or 거래가 없습니다 ({current_trade_num}/{order.total_count})")

        return order

    def _complete_trade(self, order: Order) -> None:
        """
        거래 완료 처리 + DB 저장

        Args:
            order: 주문 정보

        egg/order_module.py의 trade_complete_single() 이관 (278-344번 줄)
        """
        if not order or not order.trade_result_list:
            return

        bot_info = self.bot_info_repo.find_by_name(order.name)
        if not bot_info:
            self.message_repo.send_message(f"⚠️ [{order.name}] 봇 정보를 찾을 수 없습니다")
            return

        # dict를 TradeResult 객체로 변환
        trade_result_list = [
            self._dict_to_trade_result(tr_dict)
            for tr_dict in order.trade_result_list
            if tr_dict is not None
        ]
        trade_result = self._merge_trade_results(trade_result_list, order)

        if trade_result:
            value_msg = f"전체 구매 요청 시드 : {order.total_value:,.0f}$" \
                if self._is_buy(order) else f"전체 판매 요청 개수 {order.total_value}개"

            self.message_repo.send_message(
                f"[{order.name}] {order.total_count}개의 요청 중 유효한 {len(trade_result_list)}개의 거래 결과를 머지합니다.\n"
                f"{value_msg}\n"
                f"📊 거래 결과:\n"
                f"  - 거래 유형: {trade_result.trade_type.value}\n"
                f"  - 거래 개수: {trade_result.amount}\n"
                f"  - 거래 단가: ${trade_result.unit_price:,.2f}\n"
                f"  - 총 거래금액: ${trade_result.total_price:,.2f}\n")

            # DB 저장
            if self._is_buy(order):
                self._save_buy_to_db(bot_info, trade_result)
            else:
                self._save_sell_to_db(bot_info, trade_result)

        else:
            self.message_repo.send_message(f"[{order.name}] 유효한 거래가 없습니다")

        # 거래 완료 후 order 삭제
        self.order_repo.delete_by_name(order.name)
        print(f"[{order.name}] 주문서 삭제 완료")

    def _save_buy_to_db(self, bot_info: BotInfo, trade_result: TradeResult) -> None:
        """
        매수 DB 저장

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과

        egg/db_usecase.py의 write_buy_db() 이관 (95-110번 줄)
        """
        if not trade_result:
            self.message_repo.send_message(f"[{bot_info.name}] 거래를 찾을 수 없어 종료합니다")
            return

        msg = (f"[거래기록] {bot_info.symbol}({trade_result.trade_type})\n"
               f"총구입금액 : {float(trade_result.total_price):.2f}$\n"
               f"구매단가 : {float(trade_result.unit_price):.2f}$\n"
               f"수량 : {float(trade_result.amount):.0f}개")
        print(msg)

        prev_trade = self.trade_repo.find_by_name(bot_info.name)
        re_balancing_trade = self.trade_repo.rebalance_trade(
            name=bot_info.name,
            symbol=bot_info.symbol,
            prev_trade=prev_trade,
            trade_result=trade_result
        )
        self.trade_repo.save(re_balancing_trade)

        # 매수 History 저장
        self._save_buy_history(bot_info, trade_result, prev_trade)

    def _save_sell_to_db(self, bot_info: BotInfo, trade_result: TradeResult) -> None:
        """
        매도 DB 저장 + History

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과

        egg/db_usecase.py의 write_sell_db() 이관 (7-37번 줄)
        """
        is_update_added_seed = False
        if not trade_result:
            self.message_repo.send_message(f"[{bot_info.name}] 거래를 찾을 수 없어 종료합니다")
            return

        msg = (f"[거래완료] {bot_info.symbol}({trade_result.trade_type})\n"
               f"총판매금액 : {float(trade_result.total_price):.2f}$\n"
               f"판매단가 : {float(trade_result.unit_price):.2f}$\n"
               f"수량 : {float(trade_result.amount):.0f}개")
        self.message_repo.send_message(msg)

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

        # 매도 History 저장
        self._save_sell_history(bot_info, trade_result, prev_trade, is_update_added_seed)

    def _save_buy_history(
            self,
            bot_info: BotInfo,
            trade_result: TradeResult,
            prev_trade: Optional[Trade]
    ) -> None:
        """
        매수 History 저장

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과
            prev_trade: 이전 거래 정보 (Optional)
        """
        from domain.entities.history import History

        # date_added: prev_trade가 있으면 그 거래의 date_added, 없으면 현재 시간
        date_added = prev_trade.date_added if prev_trade else datetime.now()

        # 매수 History: sell_price=0, profit=0, profit_rate=0
        history = History(
            date_added=date_added,
            trade_date=datetime.now(),
            trade_type=trade_result.trade_type,
            name=bot_info.name,
            symbol=bot_info.symbol,
            buy_price=trade_result.unit_price,
            sell_price=0,
            amount=trade_result.amount,
            profit=0,
            profit_rate=0
        )
        self.history_repo.save(history)

    def _save_sell_history(
            self,
            bot_info: BotInfo,
            trade_result: TradeResult,
            prev_trade: Trade,
            is_update_added_seed: bool
    ) -> None:
        """
        매도 History 저장 + added_seed 업데이트

        Args:
            bot_info: 봇 정보
            trade_result: 거래 결과
            prev_trade: 이전 거래 정보
            is_update_added_seed: added_seed 업데이트 여부

        egg/db_usecase.py의 write_history_db() 이관 (40-73번 줄)
        """
        profit = round(trade_result.total_price - prev_trade.purchase_price * trade_result.amount, 2)
        profit_rate = util.get_profit_rate(
            cur_price=trade_result.unit_price,
            purchase_price=prev_trade.purchase_price
        ) / 100

        emoji = "💰" if profit > 0 else "😭"
        self.message_repo.send_message(
            f"{emoji} [{bot_info.name}] 판매기록\n"
            f"손익금 : {profit}$"
        )

        # History 저장
        from domain.entities.history import History
        history = History(
            date_added=prev_trade.date_added,
            trade_date=datetime.now(),
            trade_type=trade_result.trade_type,
            name=bot_info.name,
            symbol=bot_info.symbol,
            buy_price=prev_trade.purchase_price,
            sell_price=trade_result.unit_price,
            amount=trade_result.amount,
            profit=profit,
            profit_rate=profit_rate
        )
        self.history_repo.save(history)

        # added_seed 업데이트
        if is_update_added_seed:
            # 부분 매도 → added_seed에 수익금 추가
            bot_info.added_seed += profit * (1 / 10)
            self.bot_info_repo.save(bot_info)
        else:
            # 전체 매도 → added_seed 초기화 + 사이클 종료
            bot_info.added_seed = 0
            self.bot_info_repo.save(bot_info)
            self._finish_cycle(bot_info, prev_trade.date_added)

    def _finish_cycle(self, bot_info: BotInfo, date_added: datetime) -> None:
        """
        사이클 종료 메시지

        Args:
            bot_info: 봇 정보
            date_added: 사이클 시작 날짜

        egg/db_usecase.py의 finish_cycle() 이관 (76-92번 줄)
        """
        try:
            total = self.history_repo.get_total_sell_profit_by_name_and_date(bot_info.name, date_added)

            date_str = date_added.strftime(f'🎉축하합니다\n'
                                           f'%Y년 %m월 %d일 시작\n{bot_info.name} 사이클이 종료\n'
                                           f'최종수익금 💰{total:,.2f}$\n\n')

            history_list = self.history_repo.find_sell_by_name_and_date(bot_info.name, date_added)
            msg = ""
            for history in history_list:
                date = history.trade_date.strftime('%Y년 %m월 %d일')
                msg += f"📆{date}\n -> {history.trade_type.name} : 💰{history.profit:,.2f}$\n"

            self.message_repo.send_message(date_str + msg)
        except Exception as e:
            self.message_repo.send_message(f"사이클종료 메시지에 에러가 생겼습니다. 거래와는 무관합니다 {e}")

    def _merge_trade_results(self, trade_result_list: List[TradeResult], order: Order) -> Optional[TradeResult]:
        """
        거래 결과 병합

        Args:
            trade_result_list: 거래 결과 리스트
            order: 주문 정보 (order_type 참조용)

        Returns:
            병합된 거래 결과

        egg/order_module.py의 merged_trade() 이관 (228-253번 줄)
        수정: trade_type을 order.order_type에서 가져옴 (HantooService가 항상 SELL/BUY 반환하므로)
        """
        if not trade_result_list:
            return None

        # 수량 합계
        total_amount = sum(tr.amount for tr in trade_result_list)

        # 총 금액 합계
        total_price_sum = sum(tr.total_price for tr in trade_result_list)

        # 평단가 (가중 평균)
        avg_unit_price = round(total_price_sum / total_amount, 4)

        # trade_type은 order.order_type 사용 (부분 매도 구분을 위해)
        from domain.value_objects.trade_type import TradeType
        trade_type = TradeType(order.order_type.value)

        # 전체 매도(SELL)인데 실제 체결 수량이 원래 수량보다 적으면 → SELL_PART로 변경
        # (TWAP 부분 실패, 장 조기종료 등으로 일부만 체결된 경우)
        if trade_type == TradeType.SELL and total_amount < order.total_value:
            trade_type = TradeType.SELL_PART
            self.message_repo.send_message(
                f"⚠️ [{order.name}] TWAP 부분 체결 (장 조기종료 등)\n"
                f"  - 원래 매도 수량: {int(order.total_value)}주\n"
                f"  - 실제 체결 수량: {int(total_amount)}주\n"
                f"  - 미체결 수량: {int(order.total_value - total_amount)}주\n"
                f"  → 거래 타입 변경: SELL → SELL_PART (Trade 유지)"
            )

        # 새 TradeResult 생성
        merged = TradeResult(
            trade_type=trade_type,
            amount=total_amount,
            unit_price=avg_unit_price,
            total_price=round(total_price_sum, 2)
        )

        return merged

    def _dict_to_trade_result(self, data: Dict[str, Any]) -> Optional[TradeResult]:
        """
        dict를 TradeResult 객체로 변환

        Args:
            data: trade_result_list에서 꺼낸 dict

        Returns:
            TradeResult 객체 또는 None

        egg/order_module.py의 dict_to_trade_result() 이관 (256-275번 줄)
        """
        if data is None:
            return None

        return TradeResult(
            trade_type=TradeType(data.get('trade_type')) if data.get('trade_type') else None,
            amount=data.get('amount'),
            unit_price=data.get('unit_price'),
            total_price=data.get('total_price')
        )

