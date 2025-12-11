"""포트폴리오 상태 Usecase - 포트폴리오 정보 조회 및 동기화"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import util
from data.external.hantoo import HantooService
from domain.entities.status import Status
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.repositories.trade_repository import TradeRepository
from domain.repositories.history_repository import HistoryRepository
from domain.repositories.status_repository import StatusRepository
from domain.repositories.market_indicator_repository import MarketIndicatorRepository
from domain.value_objects.trade_type import TradeType


class PortfolioStatusUsecase:
    """포트폴리오 상태 Usecase"""

    def __init__(
            self,
            bot_info_repo: BotInfoRepository,
            trade_repo: TradeRepository,
            history_repo: HistoryRepository,
            status_repo: StatusRepository,
            hantoo_service: HantooService,
            market_indicator_repo: Optional[MarketIndicatorRepository] = None
    ):
        """
        포트폴리오 상태 Usecase 초기화

        Args:
            bot_info_repo: BotInfo 리포지토리
            trade_repo: Trade 리포지토리
            history_repo: History 리포지토리
            status_repo: Status 리포지토리
            hantoo_service: 한투 서비스
            market_indicator_repo: Market Indicator 리포지토리 (선택)
        """
        self.bot_info_repo = bot_info_repo
        self.trade_repo = trade_repo
        self.history_repo = history_repo
        self.status_repo = status_repo
        self.hantoo_service = hantoo_service
        self.market_indicator_repo = market_indicator_repo

    # ===== 조회 메서드 (Dict 반환) =====

    def get_all_bot_info(self) -> List:
        """
        모든 봇 정보 조회

        Returns:
            List[BotInfo]: 모든 봇 정보 리스트
        """
        return self.bot_info_repo.find_all()

    def get_status(self) -> Status:
        """
        입출금 정보 조회

        Returns:
            Status: 입출금 정보 (없으면 기본값 반환)
        """
        status = self.status_repo.get_status()
        if not status:
            # Status가 없으면 기본값 생성
            status = Status(
                deposit_won=0,
                deposit_dollar=0,
                withdraw_won=0,
                withdraw_dollar=0,
            )
        return status

    def save_status(self, deposit_won: float, deposit_dollar: float,
                    withdraw_won: float, withdraw_dollar: float) -> None:
        """
        입출금 정보 저장

        Args:
            deposit_won: 원화 입금액
            deposit_dollar: 달러 입금액
            withdraw_won: 원화 출금액
            withdraw_dollar: 달러 출금액
        """
        status = Status(
            deposit_won=deposit_won,
            deposit_dollar=deposit_dollar,
            withdraw_won=withdraw_won,
            withdraw_dollar=withdraw_dollar,
        )
        # 기존 Status 삭제 후 저장 (sync_status 활용)
        self.status_repo.sync_status(status)

    def get_trade_status(self, bot_info) -> Dict[str, Any]:
        """
        거래 상태 조회 (특정 봇 기준)

        Args:
            bot_info: 봇 정보

        Returns:
            Dict: 거래 상태
                {
                    "name": str,
                    "symbol": str,
                    "cur_price": float,
                    "cur_trade": {...},
                    "profit": float,
                    "profit_rate": float,
                    "max_seed": float,
                    "total_invest": float,
                    "t": float,
                    "point": float,
                    "progress_rate": float,
                    "progress_bar": str,
                    "days_passed": int,
                    "settings": {...}
                }
        """
        try:
            cur_trade = self.trade_repo.find_by_name(bot_info.name)
            if not cur_trade:
                return None

            # 현재가, 손익, 수익률
            cur_price = self.hantoo_service.get_price(bot_info.symbol)
            if cur_price is None:
                cur_price = cur_trade.purchase_price

            profit = cur_trade.amount * cur_price - cur_trade.total_price
            profit_rate = util.get_profit_rate(cur_price, cur_trade.purchase_price)

            # 시드 관련 계산
            max_seed = bot_info.seed * bot_info.max_tier
            total_invest = self.trade_repo.get_total_investment(bot_info.name)
            t = util.get_T(total_invest, bot_info.seed)
            point = util.get_point_loc(bot_info.t_div, bot_info.max_tier, t, bot_info.point_loc)

            # %지점가 계산 (평단가 * (1 + point))
            point_price = round(cur_trade.purchase_price * (1 + point), 2) if cur_trade.purchase_price else 0

            # 시드 소진률
            progress_rate = (cur_trade.total_price / max_seed) * 100 if max_seed > 0 else 0
            progress_bar = util.create_progress_bar(progress_rate)

            # 거래 시작 경과일
            today = datetime.now().date()
            added_date = cur_trade.date_added.date() if isinstance(cur_trade.date_added,
                                                                   datetime) else cur_trade.date_added
            days_passed = (today - added_date).days

            return {
                "name": bot_info.name,
                "symbol": bot_info.symbol,
                "cur_price": cur_price,
                "cur_trade": {
                    "purchase_price": cur_trade.purchase_price,
                    "amount": cur_trade.amount,
                    "total_price": cur_trade.total_price,
                    "date_added": cur_trade.date_added,
                    "days_passed": days_passed
                },
                "profit": profit,
                "profit_rate": profit_rate,
                "max_seed": max_seed,
                "total_invest": total_invest,
                "t": t,
                "point": point,
                "point_price": point_price,
                "progress_rate": progress_rate,
                "progress_bar": progress_bar
            }

        except Exception as e:
            print(f"❌ 거래 상태 조회 실패 ({bot_info.name}): {str(e)}")
            return None

    def get_portfolio_overview(self) -> Dict[str, Any]:
        """
        포트폴리오 개요 조회 (index 페이지용)

        Returns:
            Dict: 포트폴리오 개요
        """
        try:
            hantoo_balance = self.hantoo_service.get_balance() or 0.0

            invest = 0.0
            total_buy = 0.0
            active_bots = 0
            total_max_seed = 0.0
            seed_per_tier = 0.0  # 활성 봇의 1티어 시드 합계

            bot_info_list = self.bot_info_repo.find_all()
            for bot_info in bot_info_list:
                total_max_seed += bot_info.seed * bot_info.max_tier

                if bot_info.active:
                    active_bots += 1

                trade = self.trade_repo.find_by_name(bot_info.name)
                if not trade or trade.amount <= 0:
                    continue

                # 보유 중인 봇의 1티어 시드 누적
                seed_per_tier += bot_info.seed

                price = self.hantoo_service.get_price(bot_info.symbol)
                if price is None:
                    price = trade.purchase_price
                invest += trade.amount * price
                total_buy += trade.total_price

            rp = self._get_rp()
            total_balance = hantoo_balance + invest + rp

            # 현재 손익
            current_profit = invest - total_buy
            profit_rate = (current_profit / total_buy * 100) if total_buy > 0 else 0

            # 환율
            usd_krw = util.get_naver_exchange_rate()

            # 얼럿 조건 계산
            # 예수금 부족: seed_per_tier * 2 > hantoo_balance
            # 예수금 과다 (RP 매수 필요): hantoo_balance > 10000
            alert_low_balance = seed_per_tier * 2 > hantoo_balance if seed_per_tier > 0 else False
            alert_high_balance = hantoo_balance > 10000

            return {
                "total_balance": total_balance,
                "total_buy": total_buy,
                "invest": invest,
                "current_profit": current_profit,
                "profit_rate": profit_rate,
                "usd_krw": usd_krw,
                "active_bots": active_bots,
                "total_bots": len(bot_info_list),
                "total_max_seed": total_max_seed,
                "hantoo_balance": hantoo_balance,
                "seed_per_tier": seed_per_tier,
                "alert_low_balance": alert_low_balance,
                "alert_high_balance": alert_high_balance,
            }

        except Exception as e:
            print(f"❌ 포트폴리오 개요 조회 실패: {str(e)}")
            return None

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        전체 포트폴리오 요약 조회

        Returns:
            Dict: 포트폴리오 요약
                {
                    "hantoo_balance": float,
                    "invest": float,
                    "rp": float,
                    "total_balance": float,
                    "total_profit": float,
                    "total_max_seed": float,
                    "total_one_day_seed": float,
                    "total_buy": float,
                    "current_profit": float,
                    "process_rate": float,
                    "progress_bar": str,
                    "pool": float,
                    "active_bots": int,
                    "total_bots": int,
                    "status": {...},
                    "usd_krw": float
                }
        """
        try:
            bot_info_list = self.bot_info_repo.find_all()
            if not bot_info_list:
                return None

            status = self.status_repo.get_status()
            if not status:
                return None

            hantoo_balance = self.hantoo_service.get_balance()
            if hantoo_balance is None:
                hantoo_balance = 0.0

            invest = 0.0
            total_max_seed = 0.0
            total_one_day_seed = 0.0
            total_buy = 0.0
            seed_per_tier = 0.0
            max_seed = 0.0

            for bot_info in bot_info_list:
                total_max_seed += bot_info.max_tier * bot_info.seed
                if not bot_info.active:
                    continue

                trade = self.trade_repo.find_by_name(bot_info.name)
                total_one_day_seed += bot_info.seed

                if not trade:
                    continue

                if trade.amount > 0:
                    seed_per_tier += bot_info.seed
                    max_seed += bot_info.seed * bot_info.max_tier
                    price = self.hantoo_service.get_price(bot_info.symbol)
                    if price is None:
                        price = trade.purchase_price
                    invest += trade.amount * price
                    total_buy += trade.total_price

            rp = self._get_rp()
            total_profit = self.history_repo.get_total_sell_profit()
            total_balance = hantoo_balance + invest + rp
            pool = max(total_balance - total_max_seed, 0)

            # 진행률
            process_rate = total_buy / total_balance * 100 if total_balance != 0 else 0
            progress_bar = util.create_progress_bar(process_rate)

            # 현재 손익
            current_profit = invest - total_buy
            usd_krw = util.get_naver_exchange_rate()

            return {
                "hantoo_balance": hantoo_balance,
                "invest": invest,
                "rp": rp,
                "total_balance": total_balance,
                "total_profit": total_profit,
                "total_max_seed": total_max_seed,
                "total_one_day_seed": total_one_day_seed,
                "total_buy": total_buy,
                "current_profit": current_profit,
                "process_rate": process_rate,
                "progress_bar": progress_bar,
                "pool": pool,
                "active_bots": len([b for b in bot_info_list if b.active]),
                "total_bots": len(bot_info_list),
                "seed_per_tier": seed_per_tier,
                "status": {
                    "deposit_won": status.deposit_won,
                    "deposit_dollar": status.deposit_dollar,
                    "withdraw_won": status.withdraw_won,
                    "withdraw_dollar": status.withdraw_dollar
                },
                "usd_krw": usd_krw
            }

        except Exception as e:
            print(f"❌ 포트폴리오 요약 조회 실패: {str(e)}")
            return None

    def get_today_profit(self) -> Dict[str, Any]:
        """
        오늘의 수익 조회

        Returns:
            Dict: 오늘의 수익
                {
                    "total_profit": float,
                    "details": [
                        {
                            "name": str,
                            "profit": float
                        },
                        ...
                    ],
                    "usd_krw": float,
                    "today_date": str
                }
        """
        try:
            bot_info_list = self.bot_info_repo.find_all()
            details = []
            total_profit = 0.0

            for bot_info in bot_info_list:
                daily_sell_history = self.history_repo.find_today_sell_by_name(bot_info.name)
                if daily_sell_history:
                    details.append({
                        "name": bot_info.name,
                        "profit": daily_sell_history.profit
                    })
                    total_profit += daily_sell_history.profit

            usd_krw = util.get_naver_exchange_rate()
            today_date = datetime.now().date().strftime("%m월%d일")

            return {
                "total_profit": total_profit,
                "details": details,
                "usd_krw": usd_krw,
                "today_date": today_date,
                "has_profit": len(details) > 0
            }

        except Exception as e:
            print(f"❌ 오늘의 수익 조회 실패: {str(e)}")
            return {
                "total_profit": 0.0,
                "details": [],
                "usd_krw": 0.0,
                "today_date": "",
                "has_profit": False
            }

    def get_profit_summary(self) -> str:
        """
        연도별/월별 수익 요약 조회

        Returns:
            str: 수익 요약 메시지
                - 현재 연도: 월별 수익 + 총 수익
                - 이전 연도: 총 수익만
        """
        try:
            current_year = datetime.now().year
            years = self.history_repo.get_years_from_sell_date()

            if not years:
                return "📊 거래 이력이 없습니다."

            result = []

            for year in sorted(years, reverse=True):
                total_profit = self.history_repo.get_total_sell_profit_by_year(year)
                emoji = "💰" if total_profit >= 0 else "🔻"

                if year == current_year:
                    # 현재 연도 → 월별 수익 포함 (현재 월까지만 표시)
                    monthly_profits_dict = {month: profit for month, profit in
                                            self.history_repo.get_monthly_sell_profit_by_year(year)}
                    current_month = datetime.now().month

                    result.append(f"📅 {year}년 월별 수익 💰")
                    for month in range(1, current_month + 1):  # 1월부터 현재 월까지
                        profit = monthly_profits_dict.get(month, 0.0)
                        result.append(f"{month}월, 수익금 : {profit:,.2f}$")
                    result.append(f"\n{year}년 총 수익: {emoji} {total_profit:,.2f}$")
                else:
                    # 이전 연도 → 총합만
                    result.append(f"{year}년 총 수익: {emoji} {total_profit:,.2f}$")

            return "\n".join(result)

        except Exception as e:
            print(f"❌ 수익 요약 조회 실패: {str(e)}")
            return "❌ 수익 요약 조회 중 오류가 발생했습니다."

    def get_profit_summary_for_web(self) -> Dict[str, Any]:
        """
        웹용 연도별/월별 수익 요약 조회 (원화 포함)

        Returns:
            Dict: {
                'years': [
                    {
                        'year': 2025,
                        'total_profit': 1234.56,
                        'total_profit_krw': 1820000.0,
                        'is_current_year': True,
                        'monthly_profits': [
                            {'month': 1, 'profit': 100.0, 'profit_krw': 147000.0, 'exchange_rate': 1470.0},
                            {'month': 2, 'profit': 200.0, 'profit_krw': 294000.0, 'exchange_rate': 1470.0},
                            ...
                        ]
                    },
                    ...
                ],
                'has_data': bool
            }
        """
        try:
            from config.util import get_monthly_exchange_rate

            current_year = datetime.now().year
            current_month = datetime.now().month
            years = self.history_repo.get_years_from_sell_date()

            if not years:
                return {'years': [], 'has_data': False}

            years_data = []

            for year in sorted(years, reverse=True):
                total_profit = self.history_repo.get_total_sell_profit_by_year(year)
                is_current = (year == current_year)

                # 년도 총 수익 원화 계산 (현재 환율 사용)
                from config.util import get_current_exchange_rate
                current_rate = get_current_exchange_rate()
                total_profit_krw = total_profit * current_rate

                year_data = {
                    'year': year,
                    'total_profit': total_profit,
                    'total_profit_krw': total_profit_krw,
                    'is_current_year': is_current,
                    'monthly_profits': []
                }

                # 모든 년도 월별 수익 포함
                monthly_profits_dict = {
                    month: profit
                    for month, profit in self.history_repo.get_monthly_sell_profit_by_year(year)
                }

                # 현재 년도는 현재 월까지, 과거 년도는 12월까지
                max_month = current_month if is_current else 12

                for month in range(1, max_month + 1):
                    profit = monthly_profits_dict.get(month, 0.0)

                    # 월별 환율 조회
                    exchange_rate = get_monthly_exchange_rate(year, month)
                    profit_krw = profit * exchange_rate

                    year_data['monthly_profits'].append({
                        'month': month,
                        'profit': profit,
                        'profit_krw': profit_krw,
                        'exchange_rate': exchange_rate
                    })

                years_data.append(year_data)

            return {
                'years': years_data,
                'has_data': len(years_data) > 0
            }

        except Exception as e:
            print(f"❌ 웹용 수익 요약 조회 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'years': [], 'has_data': False}

    # ===== Private 헬퍼 메서드 =====

    def _get_rp(self) -> float:
        """
        RP 준비금 조회

        Returns:
            float: RP 금액
        """
        rp_trade = self.trade_repo.find_by_name("RP")
        if rp_trade:
            return rp_trade.total_price
        return 0.0

    # ===== Trade 관리 메서드 =====

    def get_all_trades(self) -> List:
        """
        모든 Trade 조회

        Returns:
            List[Trade]: 모든 Trade 리스트
        """
        return self.trade_repo.find_all()

    def update_trade(self, name: str, purchase_price: float, amount: float) -> bool:
        """
        Trade 정보 업데이트

        Args:
            name: 봇 이름
            purchase_price: 구매가
            amount: 수량

        Returns:
            bool: 성공 여부
        """
        try:
            trade = self.trade_repo.find_by_name(name)
            if not trade:
                print(f"❌ Trade not found: {name}")
                return False

            # 평단가 및 총액 계산
            total_price = purchase_price * amount

            # Trade 엔티티 업데이트
            trade.purchase_price = purchase_price
            trade.amount = amount
            trade.total_price = total_price

            # Repository를 통해 저장
            self.trade_repo.save(trade)

            print(f"✅ Trade 업데이트 완료: {name}, {purchase_price:.2f}$ x {amount:.0f} = {total_price:.2f}$")
            return True

        except Exception as e:
            print(f"❌ Trade 업데이트 실패 ({name}): {str(e)}")
            return False

    # ===== Market Indicator 조회 =====

    def get_market_data(self) -> Optional[Dict[str, Any]]:
        """
        시장 지표 데이터 조회 (VIX + 등록된 봇들의 ticker RSI)

        Returns:
            Dict: 시장 지표 데이터
                {
                    "vix": {
                        "value": float,
                        "level": str,
                        "cached_at": str,
                        "elapsed_hours": float
                    },
                    "rsi_data": {
                        "TQQQ": {
                            "value": float,
                            "level": str,
                            "cached_at": str,
                            "elapsed_hours": float
                        },
                        "SOXL": {
                            "value": float,
                            "level": str,
                            "cached_at": str,
                            "elapsed_hours": float
                        },
                        ...
                    }
                }
                또는 None (Repository가 없거나 조회 실패 시)
        """
        if not self.market_indicator_repo:
            print("⚠️ MarketIndicatorRepository가 설정되지 않았습니다")
            return None

        try:
            result = {}

            # VIX 조회
            vix = self.market_indicator_repo.get_vix()
            if vix:
                result["vix"] = {
                    "value": vix.value,
                    "level": vix.level,
                    "cached_at": vix.cached_at,
                    "elapsed_hours": vix.elapsed_hours
                }

            # 등록된 봇들의 ticker 추출 (중복 제거)
            bot_info_list = self.bot_info_repo.find_all()
            unique_tickers = set()
            for bot_info in bot_info_list:
                if bot_info.symbol:  # symbol이 있는 경우만
                    unique_tickers.add(bot_info.symbol)

            # 각 ticker별 RSI 조회
            rsi_data = {}
            for ticker in sorted(unique_tickers):  # 알파벳 순 정렬
                rsi = self.market_indicator_repo.get_rsi(ticker)
                if rsi:
                    rsi_data[ticker] = {
                        "value": rsi.value,
                        "level": rsi.level,
                        "cached_at": rsi.cached_at,
                        "elapsed_hours": rsi.elapsed_hours
                    }

            if rsi_data:
                result["rsi_data"] = rsi_data

            return result if result else None

        except Exception as e:
            print(f"❌ 시장 지표 조회 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def get_market_history_data(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        시장 지표 히스토리 데이터 조회 (VIX + 활성 봇들의 ticker RSI + 가격)

        Args:
            days: 조회 기간 (일수, 기본 30일)

        Returns:
            Dict: 시장 지표 히스토리 데이터
                {
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
                또는 None (Repository가 없거나 조회 실패 시)
        """
        if not self.market_indicator_repo:
            print("⚠️ MarketIndicatorRepository가 설정되지 않았습니다")
            return None

        try:
            result = {}

            # VIX 히스토리 조회
            vix_history = self.market_indicator_repo.get_vix_history(days=days)
            if vix_history:
                result["vix_history"] = vix_history

            # 기본 티커 (TQQQ, SOXL) + 활성화된 봇들의 ticker 추출 (중복 제거)
            default_tickers = {'TQQQ', 'SOXL'}
            bot_info_list = self.bot_info_repo.find_all()
            unique_tickers = set(default_tickers)  # 기본 티커부터 시작
            for bot_info in bot_info_list:
                if bot_info.active and bot_info.symbol:
                    unique_tickers.add(bot_info.symbol)

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

    # ===== History 관리 메서드 =====

    def get_history_by_date_range(self, start_date, end_date) -> List:
        """
        날짜 범위로 History 조회

        Args:
            start_date: 시작 날짜 (date 객체)
            end_date: 종료 날짜 (date 객체)

        Returns:
            List[History]: History 리스트 (최신순 정렬)
        """
        try:
            all_history = self.history_repo.find_all()

            # 날짜 범위 필터링
            filtered = []
            for h in all_history:
                if h.trade_date:
                    trade_date = h.trade_date.date()
                    if start_date <= trade_date <= end_date:
                        filtered.append(h)

            # 최신순 정렬
            filtered.sort(key=lambda x: x.trade_date, reverse=True)
            return filtered

        except Exception as e:
            print(f"❌ 날짜 범위 History 조회 실패: {str(e)}")
            return []

    def get_history_by_filter(self, year: int, month: int, symbol: Optional[str] = None) -> List:
        """
        필터 조건으로 History 조회

        Args:
            year: 연도
            month: 월
            symbol: 심볼 (선택)

        Returns:
            List[History]: History 리스트
        """
        try:
            if symbol and symbol.strip():
                # Symbol 필터링 포함
                histories = self.history_repo.find_by_year_month(year, month, symbol)
            else:
                # Symbol 필터링 없음
                histories = self.history_repo.find_by_year_month(year, month, None)

            return histories if histories else []

        except Exception as e:
            print(f"❌ History 조회 실패: {str(e)}")
            return []

    def add_manual_trade(
            self,
            name: str,
            symbol: str,
            purchase_price: float,
            amount: float,
            trade_type: Optional[TradeType] = None
    ) -> bool:
        """
        Trade 수동 추가

        Args:
            name: 봇 이름
            symbol: 심볼
            purchase_price: 구매가
            amount: 수량
            trade_type: 거래 타입 (기본값: BUY)

        Returns:
            bool: 성공 여부
        """
        try:
            from domain.entities import Trade

            if trade_type is None:
                trade_type = TradeType.BUY

            total_price = purchase_price * amount

            trade = Trade(
                name=name,
                symbol=symbol,
                purchase_price=round(purchase_price, 2),
                amount=amount,
                trade_type=trade_type,
                total_price=round(total_price, 2),
                date_added=datetime.now(),
                latest_date_trade=datetime.now()
            )

            self.trade_repo.save(trade)
            print(
                f"✅ Trade 수동 추가 완료: {name}, {symbol}, {purchase_price:.2f}$ x {amount:.0f} = {total_price:.2f}$ ({trade_type.value})")
            return True

        except Exception as e:
            print(f"❌ Trade 추가 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def delete_trade(self, name: str) -> bool:
        """
        Trade 삭제

        Args:
            name: 봇 이름

        Returns:
            bool: 성공 여부
        """
        try:
            trade = self.trade_repo.find_by_name(name)
            if not trade:
                print(f"❌ Trade not found: {name}")
                return False

            self.trade_repo.delete_by_name(name)
            print(f"✅ Trade 삭제 완료: {name}")
            return True

        except Exception as e:
            print(f"❌ Trade 삭제 실패 ({name}): {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def add_manual_history(
            self,
            name: str,
            symbol: str,
            buy_price: float,
            sell_price: float,
            amount: float,
            trade_type
    ) -> bool:
        """
        History 수동 추가

        Args:
            name: 봇 이름
            symbol: 심볼
            buy_price: 구매가
            sell_price: 판매가
            amount: 수량 (profit 계산용, Entity에는 저장 안됨)
            trade_type: 거래 타입 (TradeType Enum)

        Returns:
            bool: 성공 여부
        """
        try:
            from domain.entities import History
            from config import util

            # 매수일 경우 수익 계산하지 않음
            if trade_type.is_buy():
                profit = 0
                profit_rate = 0
            else:
                # 수익 계산 (egg와 동일: (sell_price - buy_price) * amount)
                profit = (sell_price - buy_price) * amount
                profit_rate = util.get_profit_rate(sell_price, buy_price) / 100

            # History 엔티티 생성
            history = History(
                date_added=datetime.now(),
                trade_date=datetime.now(),
                trade_type=trade_type,
                name=name,
                symbol=symbol,
                buy_price=round(buy_price, 2),
                sell_price=round(sell_price, 2) if trade_type.is_sell() else 0,
                amount=amount,
                profit=profit,
                profit_rate=round(profit_rate, 2)
            )

            # DB에 저장
            self.history_repo.save(history)
            print(f"✅ History 수동 추가 완료: {name}, {symbol}, {trade_type.value}, 수익 {profit:.2f}$")
            return True

        except Exception as e:
            print(f"❌ History 추가 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def get_today_trades(self) -> Dict[str, Any]:
        """
        오늘의 거래 내역 조회 (History 기반)

        오늘 발생한 모든 거래 반환 (매수/매도 모두 History에서 조회)

        Returns:
            Dict: {
                'trades': List[Dict],  # 오늘 거래 내역
                'has_trades': bool     # 거래 여부
                'buy_count': int       # 매수 건수
                'sell_count': int      # 매도 건수
            }
        """
        today = datetime.now().date()
        return self.get_trades_by_date_range(today, today)

    def get_trades_by_date_range(self, start_date, end_date) -> Dict[str, Any]:
        """
        날짜 범위로 거래 내역 조회 (History 기반)

        Args:
            start_date: 시작 날짜 (date 객체)
            end_date: 종료 날짜 (date 객체)

        Returns:
            Dict: {
                'trades': List[Dict],  # 거래 내역
                'has_trades': bool     # 거래 여부
                'buy_count': int       # 매수 건수
                'sell_count': int      # 매도 건수
            }
        """
        try:
            all_history = self.history_repo.find_all()

            trades_list = []
            for history in all_history:
                # 날짜 범위 필터링
                trade_date = history.trade_date.date()
                if trade_date < start_date or trade_date > end_date:
                    continue

                # 매수 거래
                if history.trade_type.is_buy():
                    trades_list.append({
                        'type': 'buy',
                        'name': history.name,
                        'symbol': history.symbol,
                        'purchase_price': history.buy_price,
                        'amount': int(history.amount),
                        'total_price': history.buy_price * history.amount,
                        'time': history.trade_date.strftime('%H:%M'),
                        'date': history.trade_date,
                        'date_str': history.trade_date.strftime('%m/%d')
                    })
                # 매도 거래
                else:
                    trades_list.append({
                        'type': 'sell',
                        'name': history.name,
                        'symbol': history.symbol,
                        'buy_price': history.buy_price,
                        'sell_price': history.sell_price,
                        'amount': int(history.amount),
                        'profit': history.profit,
                        'profit_rate': history.profit_rate * 100,
                        'time': history.trade_date.strftime('%H:%M'),
                        'date': history.trade_date,
                        'date_str': history.trade_date.strftime('%m/%d')
                    })

            # 시간순 정렬 (최신순)
            trades_list.sort(key=lambda x: x['date'], reverse=True)

            # 매수/매도 카운트
            buy_count = sum(1 for t in trades_list if t['type'] == 'buy')
            sell_count = sum(1 for t in trades_list if t['type'] == 'sell')

            return {
                'trades': trades_list,
                'has_trades': len(trades_list) > 0,
                'buy_count': buy_count,
                'sell_count': sell_count
            }

        except Exception as e:
            print(f"❌ 거래 조회 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'trades': [],
                'has_trades': False,
                'buy_count': 0,
                'sell_count': 0
            }
