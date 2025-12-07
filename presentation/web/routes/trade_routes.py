from datetime import datetime
from flask import render_template, request, redirect, url_for, jsonify

from data.persistence.sqlalchemy.core import SessionFactory
from presentation.web.middleware.auth_middleware import require_web_auth
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
    SQLAlchemyStatusRepository,
    SQLAlchemyOrderRepository,
)
from data.external.hantoo.hantoo_service import HantooService
from data.external.sheets.sheets_service import SheetsService
from usecase import PortfolioStatusUsecase, TradingUsecase, BotManagementUsecase
from domain.value_objects import TradeType
from config import item

from presentation.web.routes import trade_bp


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


@trade_bp.route('/trade', methods=['GET'])
def trade_template():
    """Trade 조회"""
    portfolio_usecase = _get_dependencies()
    try:
        # Usecase를 통한 조회
        trade_list = portfolio_usecase.get_all_trades()

        # 각 trade에 대한 status 정보 조회
        trade_status_map = {}
        bot_info_list = portfolio_usecase.get_all_bot_info()
        for bot_info in bot_info_list:
            status = portfolio_usecase.get_trade_status(bot_info)
            if status:
                trade_status_map[bot_info.name] = status

        return render_template(
            'trade.html',
            trade_list=trade_list,
            trade_status_map=trade_status_map
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@trade_bp.route('/save_trade', methods=['POST'])
@require_web_auth
def save_trade():
    """Trade 수정 저장"""
    portfolio_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name')
        purchase_price = float(data.get('purchase_price', 0))
        amount = float(data.get('amount', 0))

        if not name:
            return jsonify({"error": "Name required"}), 400

        # Usecase를 통한 업데이트
        success = portfolio_usecase.update_trade(name, purchase_price, amount)

        if success:
            return jsonify({"message": f"{name} trade updated"}), 200
        else:
            return jsonify({"error": f"Failed to update {name}"}), 500

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@trade_bp.route('/add_trade', methods=['POST'])
@require_web_auth
def add_trade():
    """Trade 수동 추가"""
    portfolio_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        purchase_price = float(data.get('purchase_price', 0))
        amount = float(data.get('amount', 0))

        if not name or not symbol:
            return jsonify({"error": "Name and Symbol required"}), 400

        success = portfolio_usecase.add_manual_trade(
            name=name,
            symbol=symbol,
            purchase_price=purchase_price,
            amount=amount
        )

        if success:
            return jsonify({"message": f"Trade added: {name}"}), 200
        else:
            return jsonify({"error": "Failed to add trade"}), 500

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@trade_bp.route('/delete_trade', methods=['POST'])
@require_web_auth
def delete_trade():
    """Trade 삭제"""
    portfolio_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({"error": "Name required"}), 400

        success = portfolio_usecase.delete_trade(name=name)

        if success:
            return jsonify({"message": f"Trade deleted: {name}"}), 200
        else:
            return jsonify({"error": f"Failed to delete trade: {name}"}), 500

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@trade_bp.route('/force_sell', methods=['POST'])
@require_web_auth
def force_sell():
    """강제 매도 실행"""
    try:
        data = request.get_json()
        name = data.get('name')
        sell_ratio = float(data.get('sell_ratio', 0))
        print(f"[FORCE SELL] {name} - {sell_ratio}%")

        # BotManagementUsecase로 bot_info 조회
        session_factory = SessionFactory()
        session = session_factory.create_session()
        bot_info_repo = SQLAlchemyBotInfoRepository(session)
        trade_repo = SQLAlchemyTradeRepository(session)

        bot_management_usecase = BotManagementUsecase(
            bot_info_repo=bot_info_repo,
            trade_repo=trade_repo,
        )
        bot_info = bot_management_usecase.get_bot_info_by_name(name)
        if not bot_info:
            return jsonify({"error": f"Bot not found: {name}"}), 404

        # TradingUsecase 생성 및 force_sell 호출
        history_repo = SQLAlchemyHistoryRepository(session)
        order_repo = SQLAlchemyOrderRepository(session)
        hantoo_service = HantooService(test_mode=item.is_test)

        trading_usecase = TradingUsecase(
            bot_info_repo=bot_info_repo,
            trade_repo=trade_repo,
            history_repo=history_repo,
            order_repo=order_repo,
            hantoo_service=hantoo_service
        )

        # 실제 매도 실행
        trading_usecase.force_sell(bot_info, sell_ratio)

        return jsonify({"message": f"{name} {sell_ratio}% sold"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
