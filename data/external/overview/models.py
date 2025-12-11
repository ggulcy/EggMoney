# -*- coding: utf-8 -*-
"""Overview 데이터 모델"""
from dataclasses import dataclass


@dataclass
class StockItem:
    """보유 종목 항목"""
    name: str          # 항목 이름 (봇 이름 또는 특수항목)
    ticker: str        # 티커 심볼
    amount: float      # 보유 수량
    price: float       # 구매 가격
    total_price: float # 총 금액 (수량 × 가격)
