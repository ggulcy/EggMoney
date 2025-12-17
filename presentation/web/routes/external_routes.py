"""
External Routes - 외부 조회 전용 API (인증 불필요)

Overview 서버에서 데이터 Pull용
- GET /api/external/portfolio - 포트폴리오 정보 조회
"""
from flask import Blueprint, jsonify, request

from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.external.market_data.market_indicator_repository_impl import MarketIndicatorRepositoryImpl
from data.persistence.sqlalchemy.repositories.bot_info_repository_impl import SQLAlchemyBotInfoRepository
from data.persistence.sqlalchemy.repositories.trade_repository_impl import SQLAlchemyTradeRepository
from data.external.hantoo import HantooService
from usecase.market_usecase import MarketUsecase

external_bp = Blueprint('external', __name__, url_prefix='/api/external')


def _get_dependencies():
    """의존성 초기화"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    hantoo_service = HantooService()
    market_usecase = MarketUsecase(
        market_indicator_repo=MarketIndicatorRepositoryImpl(),
        hantoo_service=hantoo_service
    )

    return bot_info_repo, trade_repo, hantoo_service, market_usecase


def _get_balance_data(bot_info_repo, trade_repo, hantoo_service) -> dict:
    """
    잔고 데이터 조회

    Returns:
        dict: {
            "stock_items": [...],
            "balance": float,
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
                "days_until_next": None,
                "pool": None
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
            "days_until_next": None,
            "pool": None
        })

    # 총 잔고(예수금) 조회
    balance = hantoo_service.get_balance()
    if balance is None:
        balance = 0.0

    return {
        "stock_items": stock_items,
        "balance": balance,
        "current_prices": current_prices,
        "total_seed": total_seed,
        "wallet_cash": 0
    }


@external_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """포트폴리오 정보 조회"""
    try:
        bot_info_repo, trade_repo, hantoo_service, _ = _get_dependencies()
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


@external_bp.route('/drawdown/<ticker>', methods=['GET'])
def get_drawdown(ticker: str):
    """
    티커의 고점 대비 하락률 조회

    Args:
        ticker: 종목 심볼 (예: QQQ, TQQQ, SOXL)
        days: 조회 기간 (쿼리 파라미터, 기본값: 90)

    Returns:
        {
            "ticker": "QQQ",
            "period_days": 80,
            "high_price": 635.77,
            "high_date": "2025-10-29",
            "current_price": 610.54,
            "current_date": "2025-12-15",
            "drawdown_rate": -0.0397  # 소수 (예: -3.97% → -0.0397)
        }
    """
    try:
        days = request.args.get('days', 90, type=int)
        _, _, _, market_usecase = _get_dependencies()
        drawdown_data = market_usecase.get_drawdown(ticker=ticker, days=days)

        if drawdown_data is None:
            return jsonify({
                "status": "error",
                "message": f"{ticker} 데이터 조회 실패"
            }), 404

        return jsonify({
            "status": "ok",
            "data": drawdown_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


