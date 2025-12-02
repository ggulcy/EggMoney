"""Google Sheets API 클라이언트"""
import os
from typing import List, Dict

import gspread


class SheetsClient:
    """Google Sheets API 클라이언트"""

    def __init__(self, credentials_path: str = None):
        """
        Google Sheets 클라이언트 초기화

        Args:
            credentials_path: Google API 인증 JSON 파일 경로
                             None이면 기본 위치에서 찾음 (google_api_secret.json)
        """
        # 인증 파일 경로 결정
        if credentials_path is None:
            # 프로젝트 루트 디렉토리에서 google_api_secret.json 찾기
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            credentials_path = os.path.join(base_dir, 'google_api_secret.json')

        # gspread 서비스 계정으로 인증
        self.gc = gspread.service_account(credentials_path)

    def open_spreadsheet(self, spreadsheet_url: str):
        """
        Google Spreadsheet 열기

        Args:
            spreadsheet_url: 스프레드시트 URL

        Returns:
            gspread.Spreadsheet: 스프레드시트 객체
        """
        return self.gc.open_by_url(spreadsheet_url)

    def get_worksheet(self, spreadsheet_url: str, sheet_name: str):
        """
        특정 워크시트 가져오기

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름

        Returns:
            gspread.Worksheet: 워크시트 객체
        """
        doc = self.open_spreadsheet(spreadsheet_url)
        return doc.worksheet(sheet_name)

    def read_cell(self, spreadsheet_url: str, sheet_name: str, cell: str) -> str:
        """
        특정 셀 값 읽기

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cell: 셀 주소 (예: 'A1', 'B2')

        Returns:
            str: 셀 값
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        return worksheet.acell(cell).value

    def read_cells(self, spreadsheet_url: str, sheet_name: str, cells: List[str]) -> Dict[str, str]:
        """
        여러 셀 값 읽기

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cells: 셀 주소 리스트 (예: ['A1', 'B2', 'C3'])

        Returns:
            Dict[str, str]: 셀 주소: 셀 값 형태의 딕셔너리
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        result = {}
        for cell in cells:
            result[cell] = worksheet.acell(cell).value
        return result

    def write_cell(self, spreadsheet_url: str, sheet_name: str, cell: str, value) -> None:
        """
        특정 셀에 값 쓰기

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cell: 셀 주소 (예: 'A1')
            value: 쓸 값
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        worksheet.update(range_name=cell, values=[[value]])

    def write_cells(self, spreadsheet_url: str, sheet_name: str, cell_range: str, values: List[List]) -> None:
        """
        여러 셀에 값 쓰기

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cell_range: 셀 범위 (예: 'A1:C10')
            values: 쓸 값 (2D 리스트)
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        worksheet.update(range_name=cell_range, values=values)

    def clear_range(self, spreadsheet_url: str, sheet_name: str, cell_range: str) -> None:
        """
        셀 범위 삭제 (빈 값으로 채우기)

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cell_range: 셀 범위 (예: 'A4:G100')
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        # 범위의 행 수 계산
        start_row = int(cell_range.split(':')[0][1:])
        end_row = int(cell_range.split(':')[1][1:])
        num_rows = end_row - start_row + 1

        # 빈 값으로 채우기
        empty_values = [['', '', '', '', '', '', '']] * num_rows
        worksheet.update(range_name=cell_range, values=empty_values)

    def format_cells(self, spreadsheet_url: str, sheet_name: str, cell_range: str, format_spec: Dict) -> None:
        """
        셀 서식 지정

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            cell_range: 셀 범위 (예: 'D4:E10')
            format_spec: 서식 딕셔너리 (예: {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}})
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        worksheet.format(cell_range, format_spec)

    def get_last_row(self, spreadsheet_url: str, sheet_name: str, column: str = 'A') -> int:
        """
        특정 열의 마지막 데이터 행 번호 조회

        Args:
            spreadsheet_url: 스프레드시트 URL
            sheet_name: 워크시트 이름
            column: 열 이름 (기본값: 'A')

        Returns:
            int: 마지막 데이터 행 번호
        """
        worksheet = self.get_worksheet(spreadsheet_url, sheet_name)
        return len(worksheet.col_values(ord(column) - ord('A') + 1))
