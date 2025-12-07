from datetime import datetime
from flask import render_template, request, jsonify, Blueprint

from data.persistence.sqlalchemy.core import SessionFactory
from presentation.web.middleware.auth_middleware import require_web_auth
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
    SQLAlchemyStatusRepository,
)
from data.external.hantoo.hantoo_service import HantooService
from data.external.sheets.sheets_service import SheetsService
from usecase import PortfolioStatusUsecase
from domain.value_objects import TradeType
from config import item

history_bp = Blueprint('history', __name__)


def _get_dependencies():
    """의존성 주입"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    hantoo_service = HantooService(test_mode=item.is_test)
    sheets_service = SheetsService()

    return PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        sheets_service=sheets_service,
    )


@history_bp.route('/history', methods=['GET', 'POST'])
def history_template():
    """History 조회 (필터링) + 수익 요약"""
    portfolio_usecase = _get_dependencies()
    try:
        year = datetime.now().year
        month = datetime.now().month
        symbol = None

        if request.method == 'POST':
            year = int(request.form.get('year', year))
            month = int(request.form.get('month', month))
            symbol = request.form.get('symbol', '').strip()

        # Usecase를 통한 조회
        history_list = portfolio_usecase.get_history_by_filter(year, month, symbol)
        profit_summary = portfolio_usecase.get_profit_summary_for_web()

        return render_template(
            'history.html',
            history_list=history_list,
            profit_summary=profit_summary,
            year=year,
            month=month,
            symbol=symbol
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@history_bp.route('/add_history', methods=['POST'])
@require_web_auth
def add_history():
    """History 수동 추가"""
    portfolio_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        buy_price = float(data.get('buy_price', 0))
        sell_price = float(data.get('sell_price', 0))
        amount = float(data.get('amount', 0))

        if not name or not symbol:
            return jsonify({"error": "Name and Symbol required"}), 400

        # Usecase를 통한 History 추가
        success = portfolio_usecase.add_manual_history(
            name=name,
            symbol=symbol,
            buy_price=buy_price,
            sell_price=sell_price,
            amount=amount,
            trade_type=TradeType.SELL
        )

        if success:
            return jsonify({"message": f"History added: {name}"}), 200
        else:
            return jsonify({"error": "Failed to add history"}), 500

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
