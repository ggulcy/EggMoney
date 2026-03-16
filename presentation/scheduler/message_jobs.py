"""메시지 작업 정의 - 텔레그램 메시지 발송

TradingJobs와 동일하게 생성자에서 의존성 주입받습니다.
"""
from datetime import datetime, timedelta

from config import util
from domain.repositories import MessageRepository
from usecase.portfolio_status_usecase import PortfolioStatusUsecase


class MessageJobs:
    """메시지 작업 클래스"""

    def __init__(
            self,
            portfolio_usecase: PortfolioStatusUsecase,
            bot_management_usecase=None,
            message_repo: MessageRepository = None
    ):
        """
        Args:
            portfolio_usecase: PortfolioStatusUsecase 인스턴스
            bot_management_usecase: BotManagementUsecase 인스턴스 (선택)
            message_repo: MessageRepository 인스턴스
        """
        self.portfolio_usecase = portfolio_usecase
        self.bot_management_usecase = bot_management_usecase
        self.message_repo = message_repo

    def send_trade_status_message(self) -> None:
        """
        각 봇별 거래 상태를 텔레그램으로 전송
        """
        print("📨 거래 상태 메시지 전송...")

        try:
            bot_info_list = self.portfolio_usecase.get_all_bot_info()

            for bot_info in bot_info_list:
                trade_status = self.portfolio_usecase.get_trade_status(bot_info)
                if not trade_status:
                    continue

                # 메시지 요소 정리
                profit = trade_status["profit"]
                profit_rate = trade_status["profit_rate"]
                profit_emoji = "🔺" if profit > 0 else "🔻"

                point = trade_status["point"]
                added_msg = f"\n🚀🚀🚀다음 거래 확률 높습니다!\n" if point * 100 < profit_rate else ""

                # 거래 시작 날짜 포맷팅
                cur_trade = trade_status["cur_trade"]
                date_added = cur_trade["date_added"]
                if isinstance(date_added, datetime):
                    added_date = date_added.date()
                else:
                    added_date = date_added
                days_passed = cur_trade["days_passed"]
                trade_start_msg = f"{added_date.year}.{added_date.month}.{added_date.day} 시작 (+{days_passed}일)"

                # 전체 메시지
                msg = (
                    f"[{trade_status['name']}]\n\n"
                    f"📌 거래\n"
                    f"{trade_start_msg}\n"
                    f"손익 : {profit:,.2f}$ ({profit_emoji} {profit_rate:.2f}%)\n"
                    f"현재가 : {trade_status['cur_price']:,.2f}$\n"
                    f"평단가 : {cur_trade['purchase_price']:,.2f}$ ({cur_trade['amount']}개)\n\n"
                    f"📌 진행률\n"
                    f"T : {trade_status['t']:.2f}T / {bot_info.max_tier:.2f}T\n"
                    f"%지점 : {point * 100:.2f}% ({cur_trade['purchase_price'] * (1 + point):,.2f}$)\n"
                    f"시드 소진률 : {trade_status['progress_rate']:,.2f}% ({cur_trade['total_price']:,.0f}/{trade_status['max_seed']:,.0f}$)\n"
                    f"{trade_status['progress_bar']}\n"
                    f"{added_msg}\n"
                )

                self.message_repo.send_message(msg)

            print(f"✅ 거래 상태 메시지 전송 완료 ({len(bot_info_list)}개 봇)")

        except Exception as e:
            print(f"❌ 거래 상태 메시지 전송 실패: {str(e)}")
            import traceback
            traceback.print_exc()

    def send_portfolio_summary_message(self) -> None:
        """
        전체 포트폴리오 요약을 텔레그램으로 전송
        """
        print("📨 포트폴리오 요약 메시지 전송...")

        try:
            summary = self.portfolio_usecase.get_portfolio_summary()
            if not summary:
                print("⚠️ 포트폴리오 요약 데이터 없음")
                return

            # 시드 대비 현금 부족 경고
            balance_msg = "🚨🚨 예수금 부족! 충전 필요\n" if summary["seed_per_tier"] * 2 > summary["hantoo_balance"] else ""

            # 활성 봇 개수 요약
            bot_active_msg = f"{summary['active_bots']}개 / 총 {summary['total_bots']}개"

            # 현재 손익
            current_profit = summary["current_profit"]
            current_profit_emoji = "🔺" if current_profit >= 0 else "🔻"
            current_profit_krw = current_profit * summary["usd_krw"]

            # 메시지 구성
            msg = (
                f" 💡 잔고\n"
                f" 예수금 : {summary['hantoo_balance']:,.0f}$ (1일 시드 : {summary['total_one_day_seed']:,.0f}$)\n"
                f"{balance_msg}\n"
                f" 📚 정보\n"
                f" 활성 봇 : {bot_active_msg}\n"
                f" 주식 평가액 : {summary['invest']:,.0f}$\n"
                f" RP : {summary['rp']:,.0f}$\n"
                f" 잔고 총합 : {summary['total_balance']:,.0f}$\n"
                f" 현금비율 : {100 - summary['process_rate']:,.2f}% ({summary['total_buy']:,.0f}/{summary['total_balance']:,.0f}$)\n"
                f"\n{summary['progress_bar']}\n\n"
                f" 💵 손익 : {current_profit:,.0f}$({current_profit_emoji}) ({current_profit_krw:,.0f}₩)\n"
                f" 누적 확정 수익 : {summary['total_profit']:,.0f}$\n"
                f" 여유 출금 가능액 : {summary['pool']:,.0f}$"
            )

            self.message_repo.send_message(msg)
            print("✅ 포트폴리오 요약 메시지 전송 완료")

        except Exception as e:
            print(f"❌ 포트폴리오 요약 메시지 전송 실패: {str(e)}")
            import traceback
            traceback.print_exc()

    def send_today_profit_message(self) -> None:
        """
        오늘의 수익을 텔레그램으로 전송 (사진 포함)
        """
        print("📨 오늘의 수익 메시지 전송...")

        try:
            profit_data = self.portfolio_usecase.get_today_profit()

            if not profit_data["has_profit"]:
                print("⚠️ 오늘 수익 없음")
                return

            # 상세 내역 메시지
            details_msg = ""
            for detail in profit_data["details"]:
                details_msg += f"[{detail['name']}] -> 💰{detail['profit']:,.0f}$\n"

            # 총수익 메시지
            total_profit = profit_data["total_profit"]
            msg_today = (
                f"금일({profit_data['today_date']})\n"
                f"수익(손절)이 존재합니다.\n\n"
                f"총수익(손절) : 💰{total_profit:,.0f}$\n"
            )

            # 원화 환산
            usd_krw_msg = ""
            if profit_data["usd_krw"] != 0:
                krw_profit = total_profit * profit_data["usd_krw"]
                tax = krw_profit * 0.22
                usd_krw_msg = (
                    f"원화 수익금(예상 양도세)\n"
                    f"₩ {krw_profit:,.0f}원(₩ {tax:,.0f}원)\n\n"
                )

            full_msg = f"{msg_today}{usd_krw_msg}{details_msg}"

            # 수익이 있으면 사진과 함께, 손절이면 텍스트만
            if total_profit > 0:
                self.message_repo.send_message(full_msg, "pepe_glass.png")
            else:
                self.message_repo.send_message(full_msg)

            print(f"✅ 오늘의 수익 메시지 전송 완료 (총 ${total_profit:,.2f})")

        except Exception as e:
            print(f"❌ 오늘의 수익 메시지 전송 실패: {str(e)}")
            import traceback
            traceback.print_exc()

    # ========================================
    # 통합 메서드
    # ========================================

    def send_all_status(self) -> None:
        """
        모든 상태 메시지 전송 (거래 상태 + 포트폴리오 요약 + 오늘 수익)
        """
        print("📨 모든 상태 메시지 전송...")
        self.send_trade_status_message()
        self.send_portfolio_summary_message()
        self.send_today_profit_message()
        print("✅ 모든 상태 메시지 전송 완료")

    def daily_job(self) -> None:
        """
        일일 작업

        1. 텔레그램 메시지 전송 (거래 상태, 포트폴리오 요약, 오늘 수익)
        2. 봇 동기화 체크
        """
        from datetime import datetime

        print("=" * 80)
        print(f"📊 일일 작업 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # self.bot_management_usecase.check_bot_sync()
        self.bot_management_usecase.auto_start_next_bots()

        # 1. 텔레그램 메시지 전송
        self.send_all_status()


        print("=" * 80)
        print("✅ 일일 작업 완료")
        print("=" * 80)
