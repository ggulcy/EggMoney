"""
External Routes - 외부 조회 전용 API (인증 불필요)

Overview 서버에서 데이터 Pull용
- GET /api/external/portfolio - 포트폴리오 정보 조회
"""
from flask import Blueprint, jsonify

from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories.bot_info_repository_impl import SQLAlchemyBotInfoRepository
from data.persistence.sqlalchemy.repositories.trade_repository_impl import SQLAlchemyTradeRepository
from data.external.hantoo import HantooService

external_bp = Blueprint('external', __name__, url_prefix='/api/external')


def _get_dependencies():
    """의존성 초기화"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    hantoo_service = HantooService()

    return bot_info_repo, trade_repo, hantoo_service


def _get_balance_data(bot_info_repo, trade_repo, hantoo_service) -> dict:
    """
    잔고 데이터 조회

    Returns:
        dict: {
            "stock_items": [...],
            "total_balance": float,
            "current_prices": {...},
            "total_seed": float  # active인 봇들의 seed 합계
        }
    """
    bot_info_list = bot_info_repo.find_all()
    stock_items = []
    current_prices = {}
    total_seed = 0.0

    # 각 봇의 거래 정보 수집
    for bot_info in bot_info_list:
        # active인 봇의 seed 합산
        if bot_info.active:
            total_seed += bot_info.seed
        trade = trade_repo.find_by_name(bot_info.name)
        if trade and trade.amount > 0:
            stock_items.append({
                "name": bot_info.name,
                "ticker": trade.symbol,
                "amount": trade.amount,
                "price": trade.purchase_price,
                "total_price": trade.total_price,
                "days_until_next": None
            })
            # 현재가 조회
            if trade.symbol not in current_prices:
                price = hantoo_service.get_price(trade.symbol)
                if price:
                    current_prices[trade.symbol] = price

    # RP 추가
    rp_trade = trade_repo.find_by_name("RP")
    if rp_trade and rp_trade.purchase_price != 0:
        stock_items.append({
            "name": "RP",
            "ticker": rp_trade.symbol,
            "amount": rp_trade.amount,
            "price": rp_trade.purchase_price,
            "total_price": rp_trade.total_price,
            "days_until_next": None
        })

    # 총 잔고(예수금) 조회
    total_balance = hantoo_service.get_balance()
    if total_balance is None:
        total_balance = 0.0

    return {
        "stock_items": stock_items,
        "total_balance": total_balance,
        "current_prices": current_prices,
        "total_seed": total_seed
    }


@external_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """포트폴리오 정보 조회"""
    try:
        bot_info_repo, trade_repo, hantoo_service = _get_dependencies()
        balance_data = _get_balance_data(bot_info_repo, trade_repo, hantoo_service)

        return jsonify({
            "status": "ok",
            "data": balance_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
