"""Google Sheets 데이터 모델"""
from dataclasses import dataclass


@dataclass
class SheetItem:
    """시트에 작성될 항목"""
    name: str          # 항목 이름 (봇 이름 또는 특수항목)
    ticker: str        # 티커 심볼
    amount: float      # 보유 수량
    price: float       # 구매 가격
    total_price: float # 총 금액 (수량 × 가격)


@dataclass
class DepositValues:
    """입금액 정보"""
    krw_deposit: float      # 원화 입금액
    usd_deposit: float      # 외화 입금액
    krw_withdrawal: float   # 원화 출금액
    usd_withdrawal: float   # 외화 출금액
