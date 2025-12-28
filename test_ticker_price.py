"""티커 가격 조회 테스트"""
import yfinance as yf


def get_stock_price(ticker: str) -> dict:
    """
    티커 입력하여 현재 가격 조회

    Args:
        ticker: 티커 심볼
                - 미국 주식: "AAPL", "TSLA" 등
                - 한국 주식: "005930.KS" (삼성전자), "035720.KS" (카카오)
                - 숫자만 입력 시 자동으로 .KS 추가 (예: "005930" -> "005930.KS")

    Returns:
        dict: {
            'ticker': 티커,
            'name': 종목명,
            'price': 현재가,
            'currency': 통화,
            'market_cap': 시가총액,
            'volume': 거래량
        }
    """
    # 숫자만 입력된 경우 한국 주식으로 간주하고 .KS 추가
    if ticker.isdigit():
        ticker = f"{ticker}.KS"

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # 현재가 조회 (여러 필드 시도)
        current_price = (
            info.get('currentPrice') or
            info.get('regularMarketPrice') or
            info.get('previousClose')
        )

        result = {
            'ticker': ticker,
            'name': info.get('longName') or info.get('shortName', 'N/A'),
            'price': current_price,
            'currency': info.get('currency', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'volume': info.get('volume', 'N/A')
        }

        return result

    except Exception as e:
        return {
            'ticker': ticker,
            'error': str(e)
        }


def format_number(num):
    """숫자 포맷팅 (천 단위 콤마)"""
    if isinstance(num, (int, float)):
        return f"{num:,.2f}"
    return num


if __name__ == "__main__":
    # 테스트 케이스
    test_tickers = [
        "AAPL",      # 애플
        "TSLA",      # 테슬라
        "005930",    # 삼성전자 (숫자만 입력)
        "035720",    # 카카오 (숫자만 입력)
        "005930.KS", # 삼성전자 (전체 티커)
    ]

    print(get_stock_price("005930"))