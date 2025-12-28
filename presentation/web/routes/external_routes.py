"""
External Routes - 외부 조회 전용 API (인증 불필요)

Overview 서버에서 데이터 Pull용
- GET /api/external/portfolio - 포트폴리오 정보 조회
"""
from flask import Blueprint, jsonify, request

from config.dependencies import get_dependencies
from usecase.market_usecase import MarketUsecase

external_bp = Blueprint('external', __name__, url_prefix='/api/external')


def _get_deps():
    """DI 컨테이너에서 의존성 조회"""
    deps = get_dependencies()
    market_usecase = MarketUsecase(
        market_indicator_repo=deps.market_indicator_repo,
        exchange_repo=deps.exchange_repo
    )
    return deps.bot_info_repo, deps.trade_repo, deps.exchange_repo, market_usecase


def _get_balance_data(bot_info_repo, trade_repo, exchange_repo) -> dict:
    """
    잔고 데이터 조회

    Returns:
        dict: {
            "stock_items": [...],  # 각 item에 current_price 포함
            "balance": float,
            "total_seed": float  # active인 봇들의 seed 합계
        }
    """
    bot_info_list = bot_info_repo.find_all()
    stock_items = []
    total_seed = 0.0

    # 각 봇의 거래 정보 수집
    for bot_info in bot_info_list:
        # active인 봇의 seed 합산
        if bot_info.active:
            total_seed += bot_info.seed
        trade = trade_repo.find_by_name(bot_info.name)
        if trade and trade.amount > 0:
            # 현재가 조회
            current_price = exchange_repo.get_price(trade.symbol)

            stock_items.append({
                "name": bot_info.name,
                "ticker": trade.symbol,
                "amount": trade.amount,
                "price": trade.purchase_price,
                "total_price": trade.total_price,
                "current_price": current_price,
                "days_until_next": None,
                "pool": None
            })

    # RP 추가 (현재가 = 구매가)
    rp_trade = trade_repo.find_by_name("RP")
    if rp_trade and rp_trade.purchase_price != 0:
        stock_items.append({
            "name": "RP",
            "ticker": rp_trade.symbol,
            "amount": rp_trade.amount,
            "price": rp_trade.purchase_price,
            "total_price": rp_trade.total_price,
            "current_price": rp_trade.purchase_price,
            "days_until_next": None,
            "pool": None
        })

    # 총 잔고(예수금) 조회
    balance = exchange_repo.get_balance()
    if balance is None:
        balance = 0.0

    return {
        "stock_items": stock_items,
        "balance": balance,
        "total_seed": total_seed,
        "wallet_cash": 0
    }


@external_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """포트폴리오 정보 조회"""
    try:
        bot_info_repo, trade_repo, exchange_repo, _ = _get_deps()
        balance_data = _get_balance_data(bot_info_repo, trade_repo, exchange_repo)

        return jsonify({
            "status": "ok",
            "data": balance_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


