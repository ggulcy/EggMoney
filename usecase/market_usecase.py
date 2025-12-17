"""Market Usecase - 시장 데이터 조회"""
from datetime import datetime
from typing import Dict, Any, Optional, Set, List, TYPE_CHECKING

from domain.repositories.market_indicator_repository import MarketIndicatorRepository

if TYPE_CHECKING:
    from data.external.hantoo.hantoo_service import HantooService


class MarketUsecase:
    """시장 데이터 Usecase"""

    def __init__(
            self,
            market_indicator_repo: MarketIndicatorRepository,
            hantoo_service: Optional["HantooService"] = None
    ):
        """
        Market Usecase 초기화

        Args:
            market_indicator_repo: MarketIndicatorRepository 인터페이스
            hantoo_service: HantooService (실시간 가격 조회용, Optional)
        """
        self.market_indicator_repo = market_indicator_repo
        self.hantoo_service = hantoo_service

    def get_drawdown(self, ticker: str, days: int = 90) -> Optional[Dict[str, Any]]:
        """
        티커의 고점 대비 하락률 조회

        Args:
            ticker: 종목 심볼 (예: QQQ, TQQQ, SOXL)
            days: 조회 기간 (기본값: 90)

        Returns:
            Dict: {
                "ticker": "QQQ",
                "period_days": 90,
                "high_price": 635.77,
                "high_date": "2025-10-29",
                "current_price": 610.54,
                "current_date": "2025-12-15",
                "drawdown_rate": -0.0397  # 소수 (예: -3.97% → -0.0397)
            }
            또는 None (조회 실패 시)
        """
        try:
            price_history = self.market_indicator_repo.get_price_history(
                ticker=ticker.upper(),
                days=days
            )

            if price_history is None or len(price_history) == 0:
                return None

            # 고점 계산
            high_price = max(item["value"] for item in price_history)
            high_date = next(
                item["date"] for item in price_history
                if item["value"] == high_price
            )

            # 현재가 (HantooService가 있으면 실시간, 없으면 yf 데이터 사용)
            if self.hantoo_service:
                current_price = self.hantoo_service.get_price(ticker.upper())
                current_date = datetime.now().strftime("%Y-%m-%d")
                if current_price is None:
                    # 실시간 조회 실패 시 yf 데이터 사용
                    current_price = price_history[-1]["value"]
                    current_date = price_history[-1]["date"]
            else:
                current_price = price_history[-1]["value"]
                current_date = price_history[-1]["date"]

            # 하락률 계산 (소수)
            drawdown_rate = round(
                (current_price - high_price) / high_price, 4
            )

            return {
                "ticker": ticker.upper(),
                "period_days": len(price_history),
                "high_price": high_price,
                "high_date": high_date,
                "current_price": current_price,
                "current_date": current_date,
                "drawdown_rate": drawdown_rate
            }

        except Exception as e:
            print(f"❌ Drawdown 조회 실패 ({ticker}): {str(e)}")
            return None

    def get_market_history_data(
            self,
            tickers: Optional[Set[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        시장 지표 히스토리 데이터 조회 (VIX + ticker별 RSI + 가격)

        Args:
            days: 조회 기간 (일수, 기본 30일)
            tickers: 조회할 티커 Set (None이면 기본값 {'TQQQ', 'SOXL'} 사용)

        Returns:
            Dict: {
                "vix_history": [{"date": "2025-12-01", "value": 15.78}, ...],
                "rsi_history": {
                    "TQQQ": [{"date": "2025-12-01", "value": 56.26}, ...],
                    ...
                },
                "price_history": {
                    "TQQQ": [{"date": "2025-12-01", "value": 85.50}, ...],
                    ...
                }
            }
            또는 None (조회 실패 시)
        """
        try:
            days = 30
            result = {}

            # VIX 히스토리 조회
            vix_history = self.market_indicator_repo.get_price_history(ticker="^VIX", days=days)
            if vix_history:
                result["vix_history"] = vix_history

            # 기본 티커 + 전달받은 티커
            default_tickers = {'TQQQ', 'SOXL'}
            unique_tickers = default_tickers.union(tickers) if tickers else default_tickers

            # 각 ticker별 RSI 히스토리 조회
            rsi_history = {}
            for ticker in sorted(unique_tickers):
                rsi_data = self.market_indicator_repo.get_rsi_history(ticker, days=days)
                if rsi_data:
                    rsi_history[ticker] = rsi_data

            if rsi_history:
                result["rsi_history"] = rsi_history

            # 각 ticker별 가격 히스토리 조회
            price_history = {}
            for ticker in sorted(unique_tickers):
                price_data = self.market_indicator_repo.get_price_history(ticker, days=days)
                if price_data:
                    price_history[ticker] = price_data

            if price_history:
                result["price_history"] = price_history

            return result if result else None

        except Exception as e:
            print(f"❌ 시장 지표 히스토리 조회 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
