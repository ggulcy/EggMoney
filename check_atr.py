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

def check_atr_detail(tickers: list, period: int = 14):
    """각 날짜별 True Range % 출력 - ATR 검증용"""
    from data.external.market_data.market_data_service import MarketDataService
    service = MarketDataService()

    for ticker in tickers:
        ticker_data = service.client.fetch_ticker_history(ticker, interval=360, cache_hours=0)
        if ticker_data is None:
            print(f"{ticker}: 데이터 없음")
            continue

        df = ticker_data.df.tail(period + 1)  # True Range 계산에 전날 종가 필요
        df = df.copy()
        df['prev_close'] = df['Close'].shift(1)
        df['tr'] = df.apply(
            lambda r: max(
                r['High'] - r['Low'],
                abs(r['High'] - r['prev_close']) if r['prev_close'] else 0,
                abs(r['Low'] - r['prev_close']) if r['prev_close'] else 0,
            ),
            axis=1
        )
        df['tr_pct'] = df['tr'] / df['prev_close'] * 100

        df_display = df.dropna(subset=['prev_close']).tail(period)
        cur_price = float(df['Close'].iloc[-1])
        simple_avg = df_display['tr_pct'].mean()

        # TR% 평균 → 현재가 곱해서 달러 변환 (실제 사용값과 동일)
        atr_pct = float(df_display['tr_pct'].mean())
        atr_dollar = atr_pct / 100 * cur_price

        print(f"\n[{ticker}] 최근 {period}일 True Range % (현재가 ${cur_price:.2f})\n" + "=" * 45)
        print(f"{'날짜':<12}  {'High':>8}  {'Low':>8}  {'PrevClose':>10}  {'TR':>7}  {'TR%':>6}")
        print("-" * 65)
        for date, row in df_display.iterrows():
            date_str = str(date)[:10]
            print(f"{date_str:<12}  ${float(row['High']):>7.2f}  ${float(row['Low']):>7.2f}  ${float(row['prev_close']):>9.2f}  ${float(row['tr']):>6.2f}  {float(row['tr_pct']):>5.2f}%")
        print("-" * 65)
        print(f"{'ATR (14일 단순평균 TR%)':>53}  {atr_pct:>5.2f}%  (${atr_dollar:.2f})")

if __name__ == "__main__":
    # 인자로 티커 넘기거나 기본값 사용
    # 예: python check_atr.py SOXL TQQQ QQQ SPY
    # 상세 검증: python check_atr.py --detail SOXL
    # if "--detail" in sys.argv:
    args = [a for a in sys.argv[1:] if a != "--detail"]
    tickers = args if args else ["SOXL"]
    check_atr_detail(tickers)
    # else:
    # tickers = sys.argv[1:] if len(sys.argv) > 1 else ["SOXL"]
    # check_atr(tickers)
