"""
External Routes - 외부 조회 전용 API (인증 불필요)

통합 서버나 다른 앱에서 데이터 조회용
- GET /api/external/deposit - 입출금 정보 조회
"""
from flask import Blueprint, jsonify

from config.item import admin, is_test
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyStatusRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
)
from data.external.hantoo import HantooService
from data.external.sheets import SheetsService
from usecase.portfolio_status_usecase import PortfolioStatusUsecase

external_bp = Blueprint('external', __name__, url_prefix='/api/external')


def _get_dependencies():
    """의존성 초기화 - 유즈케이스만 반환"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)

    hantoo_service = HantooService(test_mode=is_test)
    sheets_service = SheetsService()

    portfolio_usecase = PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        sheets_service=sheets_service,
    )

    return portfolio_usecase


@external_bp.route('/deposit', methods=['GET'])
def get_deposit():
    """입출금 정보 조회"""
    try:
        portfolio_usecase = _get_dependencies()
        status = portfolio_usecase.get_status()

        return jsonify({
            "status": "ok",
            "admin": admin.value if admin else None,
            "data": {
                "deposit": status.deposit_dollar,
                "withdraw": status.withdraw_dollar,
                "deposit_krw": status.deposit_won,
                "withdraw_krw": status.withdraw_won,
                "net_deposit": status.deposit_dollar - status.withdraw_dollar,
                "net_deposit_krw": status.deposit_won - status.withdraw_won
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
