"""
Status Routes - 입출금 관리 및 텔레그램 메시지 전송

Clean Architecture Pattern:
- GET /status - 입출금 정보 조회 화면
- POST /save_status - 입출금 정보 저장 (Fetch API)
- POST /send_trade_status - 거래 상태 메시지 전송
- POST /send_history_status - 거래 기록 메시지 전송
- POST /send_market_status - 마켓 상황 메시지 전송
"""
from flask import Blueprint, render_template, request, jsonify

from config.item import BotAdmin, is_test
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyStatusRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
)
from data.external import send_message_sync
from data.external.hantoo import HantooService
from data.external.sheets import SheetsService
from usecase.portfolio_status_usecase import PortfolioStatusUsecase
from presentation.scheduler.message_jobs import MessageJobs

status_bp = Blueprint('status', __name__)


def _initialize_dependencies():
    """의존성 초기화"""
    session_factory = SessionFactory()  # db_name 미지정 시 자동으로 egg_{admin}.db 생성
    session = session_factory.create_session()

    # Repositories
    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)

    # Services
    hantoo_service = HantooService(test_mode=is_test)
    sheets_service = SheetsService()

    # Usecases
    portfolio_usecase = PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        sheets_service=sheets_service,
    )

    # Jobs
    message_jobs = MessageJobs(
        portfolio_usecase=portfolio_usecase,
    )

    return status_repo, message_jobs, portfolio_usecase


@status_bp.route('/status', methods=['GET'])
def status_template():
    """입출금 관리 화면"""
    _, _, portfolio_usecase = _initialize_dependencies()

    # Status 정보 조회 (Usecase 활용)
    status = portfolio_usecase.get_status()

    return render_template('status.html', status=status)


@status_bp.route('/save_status', methods=['POST'])
def save_status():
    """입출금 정보 저장 (Fetch API)"""
    try:
        data = request.get_json()

        deposit_won = float(data.get('deposit_won', 0))
        deposit_dollar = float(data.get('deposit_dollar', 0))
        withdraw_won = float(data.get('withdraw_won', 0))
        withdraw_dollar = float(data.get('withdraw_dollar', 0))

        _, _, portfolio_usecase = _initialize_dependencies()

        # Status 저장 (Usecase 활용)
        portfolio_usecase.save_status(
            deposit_won=deposit_won,
            deposit_dollar=deposit_dollar,
            withdraw_won=withdraw_won,
            withdraw_dollar=withdraw_dollar
        )

        return jsonify({'message': '✅ 입출금 정보가 저장되었습니다.'})

    except Exception as e:
        print(f"❌ Error saving status: {e}")
        return jsonify({'error': f'저장 중 오류 발생: {str(e)}'}), 500


@status_bp.route('/send_trade_status', methods=['POST'])
def send_trade_status():
    """거래 상태 메시지 전송"""
    print("\n" + "=" * 80)
    print("🔔 /send_trade_status 엔드포인트 호출됨")
    print("=" * 80)

    try:
        _, message_jobs, _ = _initialize_dependencies()
        message_jobs.send_trade_status_message()

        print("=" * 80)
        print("✅ 거래 상태 메시지 전송 성공")
        print("=" * 80 + "\n")

        return jsonify({'message': '✅ 거래 상태 메시지를 전송했습니다.'})

    except Exception as e:
        error_msg = f"❌ Error sending trade status: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        send_message_sync("Failed to send Trade Status.")
        return jsonify({'error': '거래 상태 메시지 전송 실패'}), 500


@status_bp.route('/send_history_status', methods=['POST'])
def send_history_status():
    """거래 기록 메시지 전송 (시트 동기화 포함)"""
    print("\n" + "=" * 80)
    print("🔔 /send_history_status 엔드포인트 호출됨")
    print("=" * 80)

    try:
        _, message_jobs, portfolio_usecase = _initialize_dependencies()

        # 포트폴리오 요약 메시지 전송
        message_jobs.send_portfolio_summary_message()

        print("=" * 80)
        print("✅ 거래 기록 메시지 전송 성공")
        print("=" * 80 + "\n")

        return jsonify({'message': '✅ 거래 기록 메시지를 전송했습니다.'})

    except Exception as e:
        error_msg = f"❌ Error sending history status: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        send_message_sync("Failed to send History Status.")
        return jsonify({'error': '거래 기록 메시지 전송 실패'}), 500
