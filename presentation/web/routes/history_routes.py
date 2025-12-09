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

        # TradeType 목록 (매도/매수 구분)
        sell_types = [t for t in TradeType if t.is_sell()]
        buy_types = [t for t in TradeType if t.is_buy()]

        return render_template(
            'history.html',
            history_list=history_list,
            profit_summary=profit_summary,
            year=year,
            month=month,
            symbol=symbol,
            sell_types=sell_types,
            buy_types=buy_types
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@history_bp.route('/api/history', methods=['GET'])
def get_history_by_date():
    """날짜 범위 히스토리 API"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # 날짜 파싱 (YYYY-MM-DD 형식)
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            # 기본값: 1개월 전
            start_date = datetime.now().date()
            start_date = start_date.replace(month=start_date.month - 1) if start_date.month > 1 else start_date.replace(year=start_date.year - 1, month=12)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()

        portfolio_usecase = _get_dependencies()
        history_list = portfolio_usecase.get_history_by_date_range(start_date, end_date)

        # JSON 직렬화를 위한 변환
        result = []
        for h in history_list:
            result.append({
                'name': h.name,
                'symbol': h.symbol,
                'type': 'sell' if h.trade_type.is_sell() else 'buy',
                'buy_price': h.buy_price or 0,
                'sell_price': h.sell_price or 0,
                'amount': int(h.amount) if h.amount else 0,
                'profit': h.profit or 0,
                'profit_rate': (h.profit_rate * 100) if h.profit_rate else 0,
                'trade_date': h.trade_date.strftime('%m/%d %H:%M') if h.trade_date else '-'
            })

        return jsonify({'history': result})

    except ValueError as e:
        return jsonify({"error": f"날짜 형식 오류: {str(e)}"}), 400
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
        trade_type_str = data.get('trade_type', 'Sell').strip()

        if not name or not symbol:
            return jsonify({"error": "Name and Symbol required"}), 400

        # trade_type 문자열 -> Enum 변환
        try:
            trade_type = TradeType(trade_type_str)
        except ValueError:
            trade_type = TradeType.SELL  # 기본값

        # Usecase를 통한 History 추가
        success = portfolio_usecase.add_manual_history(
            name=name,
            symbol=symbol,
            buy_price=buy_price,
            sell_price=sell_price,
            amount=amount,
            trade_type=trade_type
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
