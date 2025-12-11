# -*- coding: utf-8 -*-
"""Overview 서비스 레이어 (비즈니스 로직 처리)"""
from typing import Optional, Dict, Any, List

from config.item import admin
from data.external.overview.overview_client import OverviewClient
from data.external.overview.models import StockItem


class OverviewService:
    """Overview 서비스"""

    def __init__(self):
        """Overview 서비스 초기화"""
        self.client = OverviewClient()

    def get_deposit_info(self) -> Optional[Dict[str, Any]]:
        """
        Overview 서버에서 입출금 정보 조회

        owner: admin.value (chan, choe 등)
        project: EggMoney (하드코딩)

        Returns:
            Dict: 입출금 정보
                {
                    "status": "ok",
                    "owner": "chan",
                    "project": "EggMoney",
                    "data": {
                        "deposit_krw": 원화 입금 합계,
                        "withdraw_krw": 원화 출금 합계,
                        "deposit_usd": 달러 입금 합계,
                        "withdraw_usd": 달러 출금 합계,
                        "net_deposit_krw": 원화 순입금,
                        "net_deposit_usd": 달러 순입금
                    }
                }
            또는 None (실패 시)
        """
        if not self.client.base_url:
            print("admin이 설정되지 않아 Overview 서버 주소를 알 수 없습니다.")
            return None

        if not admin:
            print("admin이 설정되지 않았습니다.")
            return None

        owner = admin.value
        project = "EggMoney"

        endpoint = "/api/deposit"
        params = {
            "owner": owner,
            "project": project
        }

        response = self.client.get_request(endpoint=endpoint, params=params)

        if response is None:
            return None

        try:
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                print(f"Overview 입출금 정보 조회 성공: {owner}/{project}")
                return data
            else:
                print(f"Overview API 오류: {data.get('message', 'Unknown error')}")
                return None

        except Exception as e:
            print(f"Overview 입출금 정보 조회 실패: {str(e)}")
            return None

    def post_portfolio(
        self,
        stock_items: List[StockItem],
        total_balance: float,
        current_prices: Dict[str, float]
    ) -> bool:
        """
        Overview 서버에 포트폴리오 데이터 전송

        Args:
            stock_items: 보유 종목 리스트
            total_balance: 예수금
            current_prices: 티커별 현재가

        Returns:
            bool: 성공 여부
        """
        if not self.client.base_url:
            print("admin이 설정되지 않아 Overview 서버 주소를 알 수 없습니다.")
            return False

        if not admin:
            print("admin이 설정되지 않았습니다.")
            return False

        owner = admin.value
        project = "EggMoney"

        # StockItem 리스트를 JSON 직렬화 가능한 형태로 변환
        stock_items_data = [
            {
                "name": item.name,
                "ticker": item.ticker,
                "amount": item.amount,
                "price": item.price,
                "total_price": item.total_price
            }
            for item in stock_items
        ]

        endpoint = "/api/portfolio"
        body = {
            "owner": owner,
            "project": project,
            "stock_items": stock_items_data,
            "total_balance": total_balance,
            "current_prices": current_prices
        }

        response = self.client.post_request(endpoint=endpoint, json_body=body)

        if response is None:
            return False

        try:
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                print(f"Overview 포트폴리오 전송 성공: {owner}/{project}, {len(stock_items)}개 종목")
                return True
            else:
                print(f"Overview API 오류: {data.get('message', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"Overview 포트폴리오 전송 실패: {str(e)}")
            return False
