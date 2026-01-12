"""Market Usecase - 시장 데이터 조회"""
from datetime import datetime
from typing import Dict, Any, Optional, Set, List, TYPE_CHECKING

from domain.repositories.market_indicator_repository import MarketIndicatorRepository
from domain.repositories import ExchangeRepository
from domain.value_objects.indicator_level import IndicatorLevel


class MarketUsecase:
    """시장 데이터 Usecase"""

    def __init__(
            self,
            market_indicator_repo: MarketIndicatorRepository,
            exchange_repo: Optional[ExchangeRepository] = None
    ):
        """
        Market Usecase 초기화

        Args:
            market_indicator_repo: MarketIndicatorRepository 인터페이스
            exchange_repo: ExchangeRepository (실시간 가격 조회용, Optional)
        """
        self.market_indicator_repo = market_indicator_repo
        self.exchange_repo = exchange_repo

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

            # 현재가 (ExchangeRepository가 있으면 실시간, 없으면 yf 데이터 사용)
            if self.exchange_repo:
                current_price = self.exchange_repo.get_price(ticker.upper())
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
            days = 90
            result = {}

            # VIX 히스토리 조회
            vix_history = self.market_indicator_repo.get_price_history(ticker="^VIX", days=days)
            if vix_history:
                result["vix_history"] = vix_history
                # VIX 현재 레벨 추가
                current_vix = vix_history[-1]["value"]
                result["vix_current"] = IndicatorLevel.from_vix(current_vix).to_dict()

            # 기본 티커 + 전달받은 티커
            default_tickers = {'TQQQ', 'SOXL'}
            unique_tickers = default_tickers.union(tickers) if tickers else default_tickers

            # 각 ticker별 RSI 히스토리 조회
            rsi_history = {}
            rsi_current = {}
            for ticker in sorted(unique_tickers):
                rsi_data = self.market_indicator_repo.get_rsi_history(ticker, days=days)
                if rsi_data:
                    rsi_history[ticker] = rsi_data
                    # RSI 현재 레벨 추가
                    current_rsi = rsi_data[-1]["value"]
                    rsi_current[ticker] = IndicatorLevel.from_rsi(current_rsi).to_dict()

            if rsi_history:
                result["rsi_history"] = rsi_history
                result["rsi_current"] = rsi_current

            # 각 ticker별 가격 히스토리 조회
            price_history = {}
            for ticker in sorted(unique_tickers):
                price_data = self.market_indicator_repo.get_price_history(ticker, days=days)
                if price_data:
                    price_history[ticker] = price_data

            if price_history:
                result["price_history"] = price_history

            # 각 ticker별 이평선 추세 조회
            ma_trend = {}
            for ticker in sorted(unique_tickers):
                trend_data = self.get_moving_average_trend(ticker)
                if trend_data:
                    ma_trend[ticker] = trend_data

            if ma_trend:
                result["ma_trend"] = ma_trend

            # 마지막 데이터 날짜 추가 (VIX 기준)
            if vix_history:
                result["last_data_date"] = vix_history[-1]["date"]

            return result if result else None

        except Exception as e:
            print(f"❌ 시장 지표 히스토리 조회 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def refresh_market_data(self, tickers: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        시장 데이터 캐시 삭제 후 재조회

        Args:
            tickers: 갱신할 티커 Set (None이면 기본값 {'TQQQ', 'SOXL', '^VIX'} 사용)

        Returns:
            Dict: {
                "success": True/False,
                "cleared_tickers": ["TQQQ", "SOXL", "^VIX"],
                "message": "..."
            }
        """
        try:
            # 기본 티커 + 전달받은 티커 + VIX
            default_tickers = {'TQQQ', 'SOXL', '^VIX'}
            target_tickers = default_tickers.union(tickers) if tickers else default_tickers

            # 캐시 삭제
            cleared = self.market_indicator_repo.clear_cache(list(target_tickers))

            return {
                "success": True,
                "cleared_tickers": cleared,
                "message": f"{len(cleared)}개 티커 캐시 삭제 완료"
            }

        except Exception as e:
            print(f"❌ 시장 데이터 갱신 실패: {str(e)}")
            return {
                "success": False,
                "cleared_tickers": [],
                "message": str(e)
            }

    def get_moving_average_trend(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        티커의 이평선 추세 조회

        Args:
            ticker: 종목 심볼 (예: QQQ, TQQQ, SOXL)

        Returns:
            Dict: {
                "ticker": "QQQ",
                "current_price": 610.54,
                "ma20": 605.23,
                "ma60": 598.77,
                "values": [610.54, 605.23, 598.77],
                "trend": {
                    "value": 610.54,
                    "level": "강한 상승 (매수 위주)",
                    "emoji": "🚀",
                    "css_class": "strong-uptrend"
                }
            }
            또는 None (조회 실패 시)
        """
        try:
            ma_status = self.market_indicator_repo.get_moving_average_status(
                ticker=ticker.upper()
            )

            if ma_status is None:
                return None

            # IndicatorLevel로 추세 판단
            trend_level = IndicatorLevel.from_moving_average(
                current_price=ma_status["current_price"],
                ma20=ma_status["ma20"],
                ma60=ma_status["ma60"]
            )

            return {
                "ticker": ticker.upper(),
                "current_price": ma_status["current_price"],
                "ma20": ma_status["ma20"],
                "ma60": ma_status["ma60"],
                "values": ma_status["values"],
                "trend": trend_level.to_dict()
            }

        except Exception as e:
            print(f"❌ 이평선 추세 조회 실패 ({ticker}): {str(e)}")
            return None
