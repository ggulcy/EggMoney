"""Google Sheets 비즈니스 로직"""
import time
from typing import List, Optional

from config import admin, BotAdmin, is_test
from data.external.sheets.sheets_client import SheetsClient
from data.external.sheets.sheets_models import StockItem, DepositValues
from data.external.telegram_client import send_message_sync


class SheetsService:
    """Google Sheets 서비스"""

    def __init__(self, credentials_path: str = None):
        """
        Sheets 서비스 초기화

        Args:
            credentials_path: Google API 인증 파일 경로
        """
        self.client = SheetsClient(credentials_path)
        self.spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1LcBa6XDKDdVzLv8nMPdHZF4R2L1OrYexqtXKPBc7VbQ'
        self.balance_sheet_name = f"{admin.name}Balance"  # egg 스타일
        self.deposit_sheet_name = f"Deposit_{admin.name}"

    def write_balance(
        self,
        stock_items: List[StockItem],
        total_balance: float,
        get_current_price_func=None
    ) -> bool:
        """
        잔고 정보를 Google Sheets에 작성

        Args:
            stock_items: StockItem 리스트
            total_balance: 총 잔고
            get_current_price_func: 현재 가격 조회 함수 (ticker: str) -> float
                                   None이면 stock_item.price 사용

        Returns:
            bool: 성공 여부
        """
        try:
            # 테스트 환경에서는 실행 안 함
            if is_test:
                return True

            # SK admin은 sheets 작업 안 함 (egg 패턴)
            if admin == BotAdmin.SK:
                return True

            worksheet = self.client.get_worksheet(self.spreadsheet_url, self.balance_sheet_name)

            # 1. 현재 데이터 마지막 행 찾기
            start_row = 4
            last_row = self.client.get_last_row(self.spreadsheet_url, self.balance_sheet_name, 'A')

            # 2. 기존 데이터 삭제 (A4부터 마지막까지)
            if last_row >= start_row:
                clear_range = f'A{start_row}:G{last_row}'
                self.client.clear_range(self.spreadsheet_url, self.balance_sheet_name, clear_range)

            # 3. 총 잔고를 C2에 작성
            self.client.write_cell(self.spreadsheet_url, self.balance_sheet_name, 'C2', total_balance)

            # 4. 셀 데이터 준비
            cell_data = []
            for stock_item in stock_items:
                if stock_item is None:
                    continue

                # 현재 가격 조회
                if stock_item.ticker == "RP":
                    # RP는 준비금이므로 구매 가격 사용
                    cur_price = stock_item.price
                else:
                    # 가격 조회 함수가 제공되었으면 사용, 아니면 구매 가격 사용
                    if get_current_price_func:
                        cur_price = get_current_price_func(stock_item.ticker)
                    else:
                        cur_price = stock_item.price

                # 현재 총액 및 수익률 계산
                cur_total = cur_price * stock_item.amount

                # 수익률 계산 (0으로 나누기 방지)
                if stock_item.total_price > 0:
                    profit_rate = ((cur_total - stock_item.total_price) / stock_item.total_price)
                else:
                    profit_rate = 0.0

                cell_data.append([
                    stock_item.name,
                    stock_item.ticker,
                    stock_item.amount,
                    stock_item.total_price,
                    cur_total,
                    profit_rate,
                    cur_total - stock_item.total_price
                ])

                # API rate limit 회피
                time.sleep(2)

            # 5. 데이터 작성
            if len(cell_data) > 0:
                end_row = start_row + len(cell_data) - 1
                worksheet.update(
                    range_name=f'A{start_row}:G{end_row}',
                    values=cell_data
                )

                # 6. 셀 서식 지정
                # 통화 서식 (D, E 열)
                self.client.format_cells(
                    self.spreadsheet_url,
                    self.balance_sheet_name,
                    f'D{start_row}:E{end_row}',
                    {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}}
                )

                # 수익률 서식 (F 열)
                self.client.format_cells(
                    self.spreadsheet_url,
                    self.balance_sheet_name,
                    f'F{start_row}:F{end_row}',
                    {'numberFormat': {'type': 'PERCENT', 'pattern': '0.00%'}}
                )

                # 손익 서식 (G 열)
                self.client.format_cells(
                    self.spreadsheet_url,
                    self.balance_sheet_name,
                    f'G{start_row}:G{end_row}',
                    {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}}
                )

            # 총 잔고 서식 (C2)
            self.client.format_cells(
                self.spreadsheet_url,
                self.balance_sheet_name,
                'C2',
                {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}}
            )

            return True

        except Exception as e:
            error_msg = f"[Sheet Error] write_balance PASS {e}"
            print(error_msg)
            send_message_sync(error_msg)
            return False

    def read_deposit_values(self) -> Optional[DepositValues]:
        """
        Google Sheets에서 입금액 정보 읽기

        Returns:
            DepositValues: 입금액 정보, 실패 시 None
        """
        try:
            # 테스트 환경에서는 실행 안 함
            if is_test:
                return None

            # SK admin은 sheets 작업 안 함 (egg 패턴)
            if admin == BotAdmin.SK:
                return None

            # 입금액 셀 읽기 (egg 스타일: B1, C1, H1, I1)
            cells_to_read = ['B1', 'C1', 'H1', 'I1']
            values = self.client.read_cells(self.spreadsheet_url, self.deposit_sheet_name, cells_to_read)

            # 문자열을 숫자로 변환
            krw_deposit = self._format_to_number(values.get('B1'))      # 원화 입금액
            usd_deposit = self._format_to_number(values.get('C1'))      # 외화 입금액
            krw_withdrawal = self._format_to_number(values.get('H1'))   # 원화 출금액
            usd_withdrawal = self._format_to_number(values.get('I1'))   # 외화 출금액

            return DepositValues(
                krw_deposit=krw_deposit,
                usd_deposit=usd_deposit,
                krw_withdrawal=krw_withdrawal,
                usd_withdrawal=usd_withdrawal
            )

        except Exception as e:
            error_msg = f"[Sheet Error] read_deposit_values PASS {e}"
            print(error_msg)
            send_message_sync(error_msg)
            return None

    @staticmethod
    def _format_to_number(target: str) -> float:
        """
        문자열을 숫자로 변환 (통화 기호 및 쉼표 제거)

        Args:
            target: 변환할 문자열

        Returns:
            float: 변환된 숫자
        """
        if target:
            try:
                # 원화(₩), 달러($), 쉼표(,) 제거
                cleaned = target.replace('₩', '').replace(',', '').replace('$', '').strip()
                return float(cleaned)
            except ValueError:
                return 0.0
        else:
            return 0.0

    def write_single_cell(self, sheet_name: str, cell: str, value) -> bool:
        """
        특정 셀에 값 작성

        Args:
            sheet_name: 워크시트 이름
            cell: 셀 주소 (예: 'A1')
            value: 작성할 값

        Returns:
            bool: 성공 여부
        """
        try:
            if is_test:
                return True

            if admin == BotAdmin.SK:
                return True

            self.client.write_cell(self.spreadsheet_url, sheet_name, cell, value)
            return True

        except Exception as e:
            error_msg = f"[Sheet Error] write_single_cell PASS {e}"
            print(error_msg)
            send_message_sync(error_msg)
            return False

    def read_single_cell(self, sheet_name: str, cell: str) -> Optional[str]:
        """
        특정 셀 값 읽기

        Args:
            sheet_name: 워크시트 이름
            cell: 셀 주소 (예: 'A1')

        Returns:
            str: 셀 값, 실패 시 None
        """
        try:
            if is_test:
                return None

            if admin == BotAdmin.SK:
                return None

            return self.client.read_cell(self.spreadsheet_url, sheet_name, cell)

        except Exception as e:
            error_msg = f"[Sheet Error] read_single_cell PASS {e}"
            print(error_msg)
            send_message_sync(error_msg)
            return None
