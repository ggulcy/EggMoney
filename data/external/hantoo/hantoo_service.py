# -*- coding: utf-8 -*-
"""한국투자증권 서비스 레이어 (비즈니스 로직 처리)"""
import json
import time
from datetime import datetime
from typing import Optional, List

from config import util
from data.external.hantoo.hantoo_client import HantooClient
from data.external.hantoo.hantoo_models import (
    PriceOutput,
    Balance1,
    Balance2,
    BalanceResult,
    OrderDetail,
    AvailableAmount,
    BalanceForTickers,
    BalanceForTickerOutput1,
    BalanceForTickerOutput2,
    BalanceForTickerOutput3,
    TickerItem
)


class HantooService:
    """한국투자증권 서비스"""

    def __init__(self, test_mode: bool = False):
        """
        한투 서비스 초기화

        Args:
            test_mode: 테스트 모드 활성화 여부
        """
        self.client = HantooClient()
        self.test_mode = test_mode

    def get_price(self, symbol: str) -> Optional[float]:
        """
        현재 가격 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 현재 가격, 조회 실패 시 None
        """
        # 테스트 모드일 경우 테스트 가격 반환
        if self.test_mode:
            test_prices = {
                "TQQQ": 52.33,  # %지점가(54.82) < 56 < 익절가(58.82)
                "SOXL": 40.46,
                "LABU": 15.0,
                "SPY": 550.0,
                "QQQ": 400.0,
                "VTI": 250.0
            }
            return test_prices.get(symbol, 100.0)

        end_point = "/uapi/overseas-price/v1/quotations/price"
        extra_header = {"tr_id": "HHDFS00000300"}
        extra_param = {
            "AUTH": "",
            "EXCD": self.client.get_hantoo_exd(symbol).price_exd,
            "SYMB": symbol
        }

        response = self.client.get_request(end_point=end_point, extra_header=extra_header, extra_param=extra_param)

        # 응답을 파싱하여 반환
        data_dict = json.loads(response.text)
        stock_data = PriceOutput(**data_dict['output'])

        if stock_data.last:
            return round(float(stock_data.last), 2)
        else:
            return None

    def get_prev_price(self, symbol: str) -> Optional[float]:
        """
        전일 종가 조회

        Args:
            symbol: 종목 심볼

        Returns:
            float: 전일 종가, 조회 실패 시 None
        """
        # 테스트 모드일 경우 테스트 가격 반환
        if self.test_mode:
            test_prices = {
                "TQQQ": 65.0,  # 전일 종가 (현재가: 60.0)
                "SOXL": 27.0,
                "LABU": 16.0,
                "SPY": 545.0,
                "QQQ": 395.0,
                "VTI": 248.0
            }
            return test_prices.get(symbol, 99.0)

        end_point = "/uapi/overseas-price/v1/quotations/price"
        extra_header = {"tr_id": "HHDFS00000300"}
        extra_param = {
            "AUTH": "",
            "EXCD": self.client.get_hantoo_exd(symbol).price_exd,
            "SYMB": symbol
        }

        response = self.client.get_request(end_point=end_point, extra_header=extra_header, extra_param=extra_param)

        # 응답을 파싱하여 반환
        data_dict = json.loads(response.text)
        stock_data = PriceOutput(**data_dict['output'])

        if stock_data.base:
            return round(float(stock_data.base), 2)
        else:
            return None

    def get_available_buy(self, symbol: str) -> Optional[float]:
        """
        매수 주문 가능 가격 조회 (현재가 + 0.5% 마진)

        Args:
            symbol: 종목 심볼

        Returns:
            float: 매수 주문 가능 가격
        """
        # 테스트 모드일 경우 현재 가격 그대로 반환
        if self.test_mode:
            return self.get_price(symbol)

        origin_price = self.get_price(symbol)
        request_price = round(origin_price * (1 + 0.02), 2)
        return request_price

    def get_available_sell(self, symbol: str) -> Optional[float]:
        """
        매도 주문 가능 가격 조회 (현재가 - 2% 마진)

        Args:
            symbol: 종목 심볼

        Returns:
            float: 매도 주문 가능 가격
        """
        # 테스트 모드일 경우 현재 가격 그대로 반환
        if self.test_mode:
            return self.get_price(symbol)

        origin_price = self.get_price(symbol)
        request_price = round(origin_price * (1 - 0.02), 2)
        return request_price

    def buy(self, symbol: str, amount: float, request_price: float) -> Optional['TradeResult']:
        """
        즉시 매수 (주문 후 체결 확인까지 대기)

        Args:
            symbol: 종목 심볼
            amount: 매수 수량
            request_price: 주문 가격

        Returns:
            TradeResult: 거래 결과, 실패 시 None
        """
        from domain.value_objects.trade_type import TradeType
        from domain.value_objects.trade_result import TradeResult

        # 테스트 모드일 경우 테스트용 거래 결과 반환
        if self.test_mode:
            trade_result = TradeResult(
                trade_type=TradeType.BUY,
                amount=amount,
                unit_price=request_price,
                total_price=round(amount * request_price, 2)
            )
            print(f"✅ [TEST MODE] 매수 완료: {amount} @ ${request_price:,.2f} = ${trade_result.total_price:,.2f}")
            return trade_result

        end_point = "/uapi/overseas-stock/v1/trading/order"
        extra_header = {"tr_id": "TTTT1002U"}
        body = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "PDNO": str(symbol),
            "ORD_QTY": str(int(amount)),
            "OVRS_ORD_UNPR": str(request_price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        buy_response = json.loads(self.client.post_request(end_point, extra_header, body).text)
        odno = buy_response["output"]["ODNO"] if buy_response["rt_cd"] == "0" else None

        if odno is not None:
            return self._perform_periodic_task(
                task_func=lambda: self._find_trade_history(odno=odno, symbol=symbol),
                fail_msg=f"{symbol} 거래 내역이 찾을 수 없습니다"
            )

        return None

    def sell(self, symbol: str, amount: float, request_price: float) -> Optional['TradeResult']:
        """
        즉시 매도 (주문 후 체결 확인까지 대기)

        Args:
            symbol: 종목 심볼
            amount: 매도 수량
            request_price: 주문 가격

        Returns:
            TradeResult: 거래 결과, 실패 시 None
        """
        from domain.value_objects.trade_type import TradeType
        from domain.value_objects.trade_result import TradeResult

        # 테스트 모드일 경우 테스트용 거래 결과 반환
        if self.test_mode:
            trade_result = TradeResult(
                trade_type=TradeType.SELL,
                amount=amount,
                unit_price=request_price,
                total_price=round(amount * request_price, 2)
            )
            print(f"✅ [TEST MODE] 매도 완료: {amount} @ ${request_price:,.2f} = ${trade_result.total_price:,.2f}")
            return trade_result

        end_point = "/uapi/overseas-stock/v1/trading/order"
        extra_header = {"tr_id": "TTTT1006U"}
        body = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "PDNO": str(symbol),
            "ORD_QTY": str(int(amount)),
            "OVRS_ORD_UNPR": str(request_price),
            "ORD_SVR_DVSN_CD": "0",
            "SLL_TYPE": "00",
            "ORD_DVSN": "00"
        }
        sell_response = json.loads(self.client.post_request(end_point, extra_header, body).text)
        odno = sell_response["output"]["ODNO"] if sell_response["rt_cd"] == "0" else None

        if odno is not None:
            return self._perform_periodic_task(
                task_func=lambda: self._find_trade_history(odno=odno, symbol=symbol),
                fail_msg=f"{symbol} 거래 내역이 찾을 수 없습니다"
            )

        return None

    def buy_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]:
        """
        매수 주문만 (주문번호만 반환, TWAP용)

        Args:
            symbol: 종목 심볼
            amount: 매수 수량
            request_price: 주문 가격

        Returns:
            str: 주문번호 (ODNO), 실패 시 None
        """
        # 테스트 모드일 경우 테스트용 주문번호 반환
        if self.test_mode:
            print(f"📝 [TEST MODE] 매수 주문: {amount} @ ${request_price:,.2f}")
            return "TEST_ODNO_BUY"

        end_point = "/uapi/overseas-stock/v1/trading/order"
        extra_header = {"tr_id": "TTTT1002U"}
        body = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "PDNO": str(symbol),
            "ORD_QTY": str(int(amount)),
            "OVRS_ORD_UNPR": str(request_price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        buy_response = json.loads(self.client.post_request(end_point, extra_header, body).text)
        odno = buy_response["output"]["ODNO"] if buy_response["rt_cd"] == "0" else None

        return odno

    def sell_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]:
        """
        매도 주문만 (주문번호만 반환, TWAP용)

        Args:
            symbol: 종목 심볼
            amount: 매도 수량
            request_price: 주문 가격

        Returns:
            str: 주문번호 (ODNO), 실패 시 None
        """
        # 테스트 모드일 경우 테스트용 주문번호 반환
        if self.test_mode:
            print(f"📝 [TEST MODE] 매도 주문: {amount} @ ${request_price:,.2f}")
            return "TEST_ODNO_SELL"

        end_point = "/uapi/overseas-stock/v1/trading/order"
        extra_header = {"tr_id": "TTTT1006U"}
        body = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "PDNO": str(symbol),
            "ORD_QTY": str(int(amount)),
            "OVRS_ORD_UNPR": str(request_price),
            "ORD_SVR_DVSN_CD": "0",
            "SLL_TYPE": "00",
            "ORD_DVSN": "00"
        }
        sell_response = json.loads(self.client.post_request(end_point, extra_header, body).text)
        odno = sell_response["output"]["ODNO"] if sell_response["rt_cd"] == "0" else None

        return odno

    def _find_trade_history(self, odno: str, symbol: str):
        """
        거래 내역 찾기 (private)

        Args:
            odno: 주문 번호
            symbol: 종목 심볼

        Returns:
            TradeResult or None
        """
        print("거래내역을 조회중입니다.")
        trade_history = self._get_trade_history(symbol=symbol)
        order_detail = self._find_output_by_odno(trade_history, odno)

        if order_detail is not None:
            print("거래내역을 찾았습니다")
            # TradeResult 객체로 변환하여 반환
            from domain.value_objects.trade_result import TradeResult
            trade_result = TradeResult(
                trade_type=None,
                amount=float(order_detail.ft_ccld_qty),
                unit_price=float(order_detail.ft_ccld_unpr3),
                total_price=float(order_detail.ft_ccld_amt3)
            )
            return trade_result
        return None

    def _get_trade_history(self, symbol: str) -> dict:
        """
        거래 내역 조회 (private)

        Args:
            symbol: 종목 심볼

        Returns:
            dict: 거래 내역 데이터
        """
        end_point = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
        extra_header = {"tr_id": "TTTS3035R"}
        extra_param = {
            "PDNO": symbol,
            "ORD_STRT_DT": util.get_previous_date(1),
            "ORD_END_DT": util.get_previous_date(0),
            "SLL_BUY_DVSN": "00",
            "CCLD_NCCS_DVSN": "01",
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "SORT_SQN": "DS",
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_NK200": "",
            "CTX_AREA_FK200": "",
        }
        return json.loads(self.client.get_request(end_point, extra_header, extra_param).text)

    @staticmethod
    def _find_output_by_odno(data: dict, odno_to_find: str) -> Optional[OrderDetail]:
        """
        주문 번호로 주문 내역 찾기 (private)

        Args:
            data: 거래 내역 데이터
            odno_to_find: 찾을 주문 번호

        Returns:
            OrderDetail or None
        """
        for item in data['output']:
            if item['odno'] == odno_to_find:
                return OrderDetail(**item)
        return None

    @staticmethod
    def _perform_periodic_task(task_func, fail_msg: str):
        """
        주기적으로 작업 실행 (private)

        Args:
            task_func: 실행할 함수
            fail_msg: 실패 메시지

        Returns:
            작업 실행 결과 또는 False
        """
        interval = 10
        end_time = time.time() + 300

        while time.time() < end_time:
            result = task_func()
            if result:
                return result
            time.sleep(interval)

        print(fail_msg)
        return False

    def get_amount_data(self, symbol: str) -> Optional[BalanceResult]:
        """
        잔고 데이터 조회

        Args:
            symbol: 종목 심볼

        Returns:
            BalanceResult: 잔고 데이터, 테스트 모드일 경우 None
        """
        # 테스트 모드일 경우 None 반환
        if self.test_mode:
            return None

        end_point = "/uapi/overseas-stock/v1/trading/inquire-balance"
        extra_header = {"tr_id": "TTTS3012R"}
        extra_param = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_NK200": "",
            "CTX_AREA_FK200": "",
        }

        data = json.loads(self.client.get_request(end_point, extra_header, extra_param).text)

        # 데이터 클래스로 변환하여 반환
        output1_objects = [Balance1(**item) for item in data['output1']]
        output2_object = Balance2(**data['output2'])

        return BalanceResult(
            ctx_area_fk200=data['ctx_area_fk200'],
            ctx_area_nk200=data['ctx_area_nk200'],
            output1=output1_objects,
            output2=output2_object,
            rt_cd=data['rt_cd'],
            msg_cd=data['msg_cd'],
            msg1=data['msg1']
        )

    def get_ticker_list_info(self, ticker_list: List[str] = None) -> List[TickerItem]:
        """
        종목 목록별 정보 조회

        Args:
            ticker_list: 조회할 종목 목록

        Returns:
            List[TickerItem]: 종목 정보 목록
        """
        ticker_items = []
        if ticker_list is None:
            return ticker_items

        balance_result = self.get_amount_data('TQQQ')
        if balance_result is None:
            return ticker_items

        for balance in balance_result.output1:
            if balance.ovrs_pdno in ticker_list:
                ticker_items.append(TickerItem(
                    ticker=balance.ovrs_pdno,
                    amount=float(balance.ord_psbl_qty),
                    price=float(balance.now_pric2),
                    total_price=float(balance.ovrs_stck_evlu_amt)
                ))

        return ticker_items

    @staticmethod
    def _get_ord_psbl_qty(amount_data: BalanceResult, symbol: str) -> Optional[str]:
        """
        주문 가능 수량 조회 (private)

        Args:
            amount_data: 잔고 데이터
            symbol: 종목 심볼

        Returns:
            str: 주문 가능 수량
        """
        for balance in amount_data.output1:
            if balance.ovrs_pdno == symbol:
                return balance.ord_psbl_qty
        return None

    def get_balance(self, symbol: str = 'TQQQ', price: float = 50.0) -> float:
        """
        주문 가능 금액 조회

        Args:
            symbol: 종목 심볼
            price: 가격

        Returns:
            float: 주문 가능 금액
        """
        # 테스트 모드일 경우 고정 금액 반환
        if self.test_mode:
            return 30000.0

        end_point = "/uapi/overseas-stock/v1/trading/inquire-psamount"
        extra_header = {"tr_id": "TTTS3007R"}
        extra_param = {
            "OVRS_EXCG_CD": self.client.get_hantoo_exd(symbol).trading_exd,
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }

        data = json.loads(self.client.get_request(end_point, extra_header, extra_param).text)
        result = AvailableAmount(**data['output'])
        return float(result.ovrs_ord_psbl_amt)

    def get_amount_ticker_balance(self, ticker_list: List[str] = None) -> List[TickerItem]:
        """
        티커별 잔고 조회

        Args:
            ticker_list: 조회할 종목 목록

        Returns:
            List[TickerItem]: 티커별 잔고 정보
        """
        if ticker_list is None:
            ticker_list = []

        # 테스트 모드일 경우 빈 리스트 반환
        if self.test_mode:
            return []

        end_point = "/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance"
        extra_header = {
            "tr_id": "CTRP6010R",
            "custtype": "P"
        }
        date = datetime.now().strftime('%Y%m%d')
        extra_param = {
            "BASS_DT": f"{date}",
            "WCRC_FRCR_DVSN_CD": "02",
            "INQR_DVSN_CD": "00"
        }

        data = json.loads(self.client.get_request(end_point, extra_header, extra_param).text)

        # BalanceForTickers 형태로 데이터 파싱
        result = BalanceForTickers(
            output1=[BalanceForTickerOutput1(**item) for item in data['output1']],
            output2=[BalanceForTickerOutput2(**item) for item in data['output2']],
            output3=BalanceForTickerOutput3(**data['output3']),
            rt_cd=data['rt_cd'],
            msg_cd=data['msg_cd'],
            msg1=data['msg1']
        )

        # ticker_list에 포함된 pdno만 필터링하여 변환
        filtered_result = [
            TickerItem(
                ticker=ticker.pdno,
                amount=float(ticker.ord_psbl_qty1),
                price=float(ticker.ovrs_now_pric1),
                total_price=round(float(ticker.ord_psbl_qty1) * float(ticker.ovrs_now_pric1), 3)
            )
            for ticker in result.output1 if ticker.pdno in ticker_list
        ]

        return filtered_result
