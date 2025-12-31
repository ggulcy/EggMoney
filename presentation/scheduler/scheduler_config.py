"""
EggMoney APScheduler 설정 및 관리 모듈

egg/schedule_module.py를 기반으로 작성한 APScheduler 통합 모듈입니다.
모든 초기화 로직을 내부에서 처리하여 main에서는 단순 호출만 합니다.
"""
import traceback
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import item
from config.util import get_schedule_times, is_trade_date
from config.dependencies import get_dependencies
from presentation.scheduler.trading_jobs import TradingJobs
from presentation.scheduler.message_jobs import MessageJobs
from usecase.order_usecase import OrderUsecase
from usecase.trading_usecase import TradingUsecase
from usecase.portfolio_status_usecase import PortfolioStatusUsecase
from usecase.bot_management_usecase import BotManagementUsecase
from usecase.market_usecase import MarketUsecase

# KST 시간대 명시 (서버 다른 프로그램과 충돌 방지)
KST = pytz.timezone('Asia/Seoul')

# 전역 인스턴스 (메모리 누수 방지를 위해 전역 유지)
_scheduler: Optional[BackgroundScheduler] = None
_trading_jobs: Optional['TradingJobs'] = None
_message_jobs: Optional['MessageJobs'] = None


def _initialize_dependencies() -> tuple[TradingJobs, MessageJobs]:
    """
    DI 컨테이너에서 의존성을 주입받아 Job 인스턴스들을 초기화합니다.

    Returns:
        (trading_jobs, message_jobs)
    """
    print("📦 Dependencies 초기화 중...")

    # DI 컨테이너에서 의존성 조회
    deps = get_dependencies()

    # Usecase 초기화 (의존성 주입)
    order_usecase = OrderUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        order_repo=deps.order_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
    )
    trading_usecase = TradingUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        order_repo=deps.order_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
    )
    market_usecase = MarketUsecase(
        market_indicator_repo=deps.market_indicator_repo,
        exchange_repo=deps.exchange_repo,
    )
    bot_management_usecase = BotManagementUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
        market_usecase=market_usecase,
    )

    # TradingJobs 초기화
    trading_jobs = TradingJobs(
        order_usecase=order_usecase,
        trading_usecase=trading_usecase,
        bot_management_usecase=bot_management_usecase,
        bot_info_repo=deps.bot_info_repo,
        order_repo=deps.order_repo,
        message_repo=deps.message_repo,
    )

    # MessageJobs 초기화
    portfolio_usecase = PortfolioStatusUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        exchange_repo=deps.exchange_repo,
    )

    message_jobs = MessageJobs(
        portfolio_usecase=portfolio_usecase,
        bot_management_usecase=bot_management_usecase,
        message_repo=deps.message_repo,
    )

    print("✅ Dependencies 초기화 완료")

    return trading_jobs, message_jobs


def _create_make_order_job(trading_jobs: TradingJobs):
    """메인 거래 작업 팩토리 (클로저)"""

    def make_order_job_impl():
        from datetime import datetime
        deps = get_dependencies()
        print(f"\n🤖 trade_job() called at {datetime.now()}")

        try:
            if is_trade_date():
                trading_jobs.make_order_job()
        except Exception as e:
            error_message = f"❌ [trade_job] 거래중 문제가 발생하였습니다. 문제를 확인하세요.\n{e}\n{traceback.format_exc()}"
            deps.message_repo.send_message(error_message)
            stop_scheduler()

        print(f"✅ trade_job() completed at {datetime.now()}\n")

    return make_order_job_impl


def _create_twap_job(trading_jobs: TradingJobs):
    """TWAP 거래 작업 팩토리 (클로저)"""

    def twap_job_impl():
        deps = get_dependencies()

        try:
            trading_jobs.twap_job()
        except Exception as e:
            error_message = f"❌ [twap_job] 거래중 문제가 발생하였습니다. 문제를 확인하세요.\n{e}\n{traceback.format_exc()}"
            deps.message_repo.send_message(error_message)
            stop_scheduler()

        print(f"✅ twap_job() completed at {datetime.now()}\n")

    return twap_job_impl


def _create_msg_job(message_jobs: MessageJobs):
    """메시지 전송 작업 팩토리 (클로저)"""

    def msg_job_impl():
        from datetime import datetime
        deps = get_dependencies()

        try:
            if is_trade_date():
                message_jobs.daily_job()
        except Exception as e:
            error_message = f"❌ [msg_job] 치명적 오류 발생!\n{e}\n{traceback.format_exc()}"
            deps.message_repo.send_message(error_message)
            raise  # ← 스케줄러가 job을 disable하도록

        print(f"✅ msg_job() completed at {datetime.now()}\n")

    return msg_job_impl


def _register_jobs(job_func, times: list, job_id_prefix: str) -> None:
    """
    스케줄러에 작업 등록 (공통 로직)

    Args:
        job_func: 실행할 job 함수
        times: 실행 시간 리스트 (예: ['04:35', '05:00'])
        job_id_prefix: job ID 접두사 (예: 'msg_job', 'trade_job')
    """
    for time_str in times:
        hour, minute = time_str.split(':')
        _scheduler.add_job(
            job_func,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=KST),
            id=f'{job_id_prefix}_{time_str}',
            replace_existing=True
        )
        print(f"✅ {job_id_prefix} at {time_str}")


def start_scheduler():
    """
    스케줄러를 시작합니다.
    (main에서는 이 함수만 호출하면 됨)

    - 첫 호출: Dependencies 초기화 + 스케줄러 시작
    - 재호출 (설정 변경 등): 기존 Dependencies 재사용 + 스케줄만 재등록
    """
    global _scheduler, _trading_jobs, _message_jobs

    print("🔄 Scheduler 시작...")

    # DI 컨테이너에서 MessageRepository 조회
    deps = get_dependencies()
    message_repo = deps.message_repo

    # Dependencies 초기화 (첫 호출에만)
    if _trading_jobs is None or _message_jobs is None:
        print("📦 첫 호출 - Dependencies 초기화")
        _trading_jobs, _message_jobs = _initialize_dependencies()

        # 초기화 작업 (첫 호출에만)
        print("\n📨 초기화 작업 실행...")
        message_repo.send_message(f"프로그램을 재시작합니다 {item.is_test}")
    else:
        print("♻️ 재호출 - 기존 Dependencies 재사용 (스케줄만 재등록)")
        message_repo.send_message("설정이 변경되어 스케줄을 재등록합니다")

    # 스케줄 시간 설정 (매번 새로 읽음)
    job_times, msg_times, twap_times = get_schedule_times()

    # APScheduler 생성 (첫 호출에만)
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=KST)

    # 기존 작업 제거 후 재등록
    _scheduler.remove_all_jobs()
    _register_jobs(_create_msg_job(_message_jobs), msg_times, 'msg_job')
    _register_jobs(_create_make_order_job(_trading_jobs), job_times, 'trade_job')
    _register_jobs(_create_twap_job(_trading_jobs), twap_times, 'twap_job')

    # 스케줄러 시작 (첫 호출에만)
    if not _scheduler.running:
        _scheduler.start()
        print(f"\n🚀 Scheduler started (timezone: {KST})")
    else:
        print(f"\n🔄 Scheduler running (스케줄 재등록 완료)")

    # 등록된 작업 출력
    jobs = _scheduler.get_jobs()
    print(f"\n📋 등록된 작업 ({len(jobs)}개):")
    for j in jobs:
        print(f"  - {j.id}: next_run={j.next_run_time}")
    print()


def stop_scheduler():
    """스케줄러를 중지합니다."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        print("⏹️ Scheduler stopped.")
