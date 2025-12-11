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
from config.item import is_test
from data.persistence.sqlalchemy.core.session_factory import SessionFactory
from data.persistence.sqlalchemy.repositories import (
    SQLAlchemyBotInfoRepository,
    SQLAlchemyStatusRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyHistoryRepository,
)
from data.external.hantoo import HantooService
from data.external.market_data.market_indicator_repository_impl import MarketIndicatorRepositoryImpl
from usecase.portfolio_status_usecase import PortfolioStatusUsecase

index_bp = Blueprint('index', __name__)


def _get_portfolio_usecase():
    """PortfolioStatusUsecase 초기화 (MarketIndicatorRepo 포함)"""
    session_factory = SessionFactory()
    session = session_factory.create_session()

    bot_info_repo = SQLAlchemyBotInfoRepository(session)
    status_repo = SQLAlchemyStatusRepository(session)
    trade_repo = SQLAlchemyTradeRepository(session)
    history_repo = SQLAlchemyHistoryRepository(session)
    market_indicator_repo = MarketIndicatorRepositoryImpl()

    hantoo_service = HantooService(test_mode=is_test)

    return PortfolioStatusUsecase(
        bot_info_repo=bot_info_repo,
        trade_repo=trade_repo,
        history_repo=history_repo,
        status_repo=status_repo,
        hantoo_service=hantoo_service,
        market_indicator_repo=market_indicator_repo,
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
    bot_info_list = portfolio_usecase.get_all_bot_info()
    for bot_info in bot_info_list:
        status = portfolio_usecase.get_trade_status(bot_info)
        if status:
            trade_status_map[bot_info.name] = status

    return render_template(
        'index.html',
        title='EggMoney Trading Bot',
        admin=item.admin.value,
        overview=overview,
        today_trades=today_trades,
        current_year_profit=current_year_data,
        trade_list=trade_list,
        trade_status_map=trade_status_map
    )


@index_bp.route('/api/market_history', methods=['GET'])
def get_market_history():
    """시장 지표 히스토리 API"""
    days = request.args.get('days', 30, type=int)

    portfolio_usecase = _get_portfolio_usecase()
    market_history = portfolio_usecase.get_market_history_data(days=days)

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
