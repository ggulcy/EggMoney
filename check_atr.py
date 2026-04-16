"""ATR 확인 스크립트 - 티커별 ATR 값 출력"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.external.market_data.market_indicator_repository_impl import MarketIndicatorRepositoryImpl

def check_atr(tickers: list, period: int = 14):
    repo = MarketIndicatorRepositoryImpl()

    print(f"\nATR 조회 (period={period}일)\n" + "=" * 50)
    print(f"{'티커':<10}  {'현재가':>10}  {'ATR($)':>8}  {'ATR(%)':>8}")
    print("-" * 50)
    for ticker in tickers:
        atr = repo.get_atr(ticker=ticker, period=period)
        price_history = repo.get_price_history(ticker=ticker, days=1)
        cur_price = price_history[-1]["value"] if price_history else None

        if atr and cur_price:
            atr_pct = atr / cur_price * 100
            print(f"{ticker:<10}  ${cur_price:>9.2f}  ${atr:>7.2f}  {atr_pct:>7.2f}%")
        else:
            print(f"{ticker:<10}  조회 실패")

if __name__ == "__main__":
    # 인자로 티커 넘기거나 기본값 사용
    # 예: python check_atr.py SOXL TQQQ QQQ SPY
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["SOXL", "TQQQ", "QQQ", "SPY"]
    check_atr(tickers)
