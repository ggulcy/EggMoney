"""
Index Routes - 메인 페이지

Clean Architecture Pattern:
- GET / - 메인 페이지 (메뉴 네비게이션 + 포트폴리오 요약)
- GET /api/market_history - 시장 지표 히스토리 API
- GET /api/trades - 날짜 범위 거래 내역 API
"""
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request

from config import item
from config.dependencies import get_dependencies
from usecase.portfolio_status_usecase import PortfolioStatusUsecase
from usecase.market_usecase import MarketUsecase

index_bp = Blueprint('index', __name__)


def _get_portfolio_usecase():
    """DI 컨테이너에서 PortfolioStatusUsecase 초기화"""
    deps = get_dependencies()

    return PortfolioStatusUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        exchange_repo=deps.exchange_repo,
    )


def _get_market_usecase():
    """DI 컨테이너에서 MarketUsecase 초기화"""
    deps = get_dependencies()

    return MarketUsecase(
        market_indicator_repo=deps.market_indicator_repo,
        exchange_repo=deps.exchange_repo
    )


@index_bp.route('/', methods=['GET'])
def index():
    """메인 페이지"""
    portfolio_usecase = _get_portfolio_usecase()
    overview = portfolio_usecase.get_portfolio_overview()
    today_trades = portfolio_usecase.get_today_trades()

    # 현재 년도 수익 요약 가져오기
    profit_summary = portfolio_usecase.get_profit_summary_for_web()
    current_year_data = None
    if profit_summary and profit_summary.get('has_data'):
        # 현재 년도 데이터만 필터링
        for year_data in profit_summary['years']:
            if year_data['is_current_year']:
                current_year_data = year_data
                break

    # Trade 리스트 및 상태 정보 가져오기
    trade_list = portfolio_usecase.get_all_trades()
    trade_status_map = {}
    dynamic_trade_status_map = {}
    bot_info_list = portfolio_usecase.get_all_bot_info()
    for bot_info in bot_info_list:
        status = portfolio_usecase.get_trade_status(bot_info)
        if status:
            trade_status_map[bot_info.name] = status

        dynamic_status = portfolio_usecase.get_trade_status(bot_info, use_dynamic_seed=True)
        if dynamic_status:
            dynamic_trade_status_map[bot_info.name] = dynamic_status

    return render_template(
        'index.html',
        title='EggMoney Trading Bot',
        admin=item.admin.value,
        overview=overview,
        today_trades=today_trades,
        current_year_profit=current_year_data,
        trade_list=trade_list,
        trade_status_map=trade_status_map,
        dynamic_trade_status_map=dynamic_trade_status_map
    )


@index_bp.route('/api/market_history', methods=['GET'])
def get_market_history():
    """시장 지표 히스토리 API"""

    # 활성 봇들의 tickers 조회
    portfolio_usecase = _get_portfolio_usecase()
    bot_info_list = portfolio_usecase.get_all_bot_info()
    active_tickers = {bot.symbol for bot in bot_info_list if bot.active and bot.symbol}

    # MarketUsecase로 시장 데이터 조회
    market_usecase = _get_market_usecase()
    market_history = market_usecase.get_market_history_data(tickers=active_tickers)

    if market_history:
        return jsonify(market_history)
    else:
        return jsonify({"error": "시장 지표 히스토리 조회 실패"}), 500


@index_bp.route('/api/trades', methods=['GET'])
def get_trades_by_date():
    """날짜 범위 거래 내역 API"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # 날짜 파싱 (YYYY-MM-DD 형식)
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = datetime.now().date()

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()

        portfolio_usecase = _get_portfolio_usecase()
        trades_data = portfolio_usecase.get_trades_by_date_range(start_date, end_date)

        # date 객체는 JSON 직렬화 불가하므로 제거
        for trade in trades_data.get('trades', []):
            if 'date' in trade:
                del trade['date']

        return jsonify(trades_data)

    except ValueError as e:
        return jsonify({"error": f"날짜 형식 오류: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@index_bp.route('/api/refresh_market_indicator', methods=['POST'])
def refresh_market_indicator():
    """시장 지표 강제 리프레시 API"""
    try:
        # 활성 봇들의 tickers 조회
        portfolio_usecase = _get_portfolio_usecase()
        bot_info_list = portfolio_usecase.get_all_bot_info()
        active_tickers = {bot.symbol for bot in bot_info_list if bot.active and bot.symbol}

        # 캐시 삭제
        market_usecase = _get_market_usecase()
        result = market_usecase.refresh_market_data(tickers=active_tickers)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
