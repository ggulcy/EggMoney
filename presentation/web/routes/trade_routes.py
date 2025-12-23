from datetime import datetime
from flask import render_template, request, redirect, url_for, jsonify

from config.dependencies import get_dependencies
from presentation.web.middleware.auth_middleware import require_web_auth
from usecase import PortfolioStatusUsecase, TradingUsecase, BotManagementUsecase
from domain.value_objects import TradeType
from presentation.scheduler.message_jobs import MessageJobs

from presentation.web.routes import trade_bp


def _get_portfolio_usecase():
    """DI 컨테이너에서 PortfolioStatusUsecase 초기화"""
    deps = get_dependencies()

    return PortfolioStatusUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        exchange_repo=deps.exchange_repo,
    )


def _get_trading_usecase():
    """DI 컨테이너에서 TradingUsecase 초기화"""
    deps = get_dependencies()

    return TradingUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        history_repo=deps.history_repo,
        order_repo=deps.order_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
    )


def _get_bot_management_usecase():
    """DI 컨테이너에서 BotManagementUsecase 초기화"""
    deps = get_dependencies()

    return BotManagementUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
    )


@trade_bp.route('/trade', methods=['GET'])
def trade_template():
    """Trade 조회"""
    portfolio_usecase = _get_portfolio_usecase()
    try:
        # Usecase를 통한 조회
        trade_list = portfolio_usecase.get_all_trades()

        # 각 trade에 대한 status 정보 조회
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

        # TradeType 목록 (매도/매수 구분)
        sell_types = [t for t in TradeType if t.is_sell()]
        buy_types = [t for t in TradeType if t.is_buy()]

        return render_template(
            'trade.html',
            trade_list=trade_list,
            trade_status_map=trade_status_map,
            dynamic_trade_status_map=dynamic_trade_status_map,
            sell_types=sell_types,
            buy_types=buy_types
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
    portfolio_usecase = _get_portfolio_usecase()
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
    portfolio_usecase = _get_portfolio_usecase()
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        purchase_price = float(data.get('purchase_price', 0))
        amount = float(data.get('amount', 0))
        trade_type_str = data.get('trade_type', 'Buy').strip()

        if not name or not symbol:
            return jsonify({"error": "Name and Symbol required"}), 400

        # trade_type 문자열 -> Enum 변환
        try:
            trade_type = TradeType(trade_type_str)
        except ValueError:
            trade_type = TradeType.BUY  # 기본값

        success = portfolio_usecase.add_manual_trade(
            name=name,
            symbol=symbol,
            purchase_price=purchase_price,
            amount=amount,
            trade_type=trade_type
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
    portfolio_usecase = _get_portfolio_usecase()
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


@trade_bp.route('/estimate_capital_gains_tax_fee', methods=['POST'])
@require_web_auth
def estimate_capital_gains_tax_fee():
    """양도세처리 예상 수수료 조회"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({"error": "Name required"}), 400

        trading_usecase = _get_trading_usecase()
        result = trading_usecase.estimate_capital_gains_tax_fee(name)

        if not result:
            return jsonify({"error": f"[{name}] Trade를 찾을 수 없거나 수량이 없습니다"}), 404

        return jsonify(result), 200

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@trade_bp.route('/capital_gains_tax', methods=['POST'])
@require_web_auth
def capital_gains_tax():
    """양도세처리 실행"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({"error": "Name required"}), 400

        trading_usecase = _get_trading_usecase()
        result = trading_usecase.execute_capital_gains_tax_wash(name)

        if not result:
            return jsonify({"error": f"[{name}] 양도세처리 실패"}), 500

        return jsonify({
            "message": f"[{name}] 양도세처리 완료",
            "result": result
        }), 200

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

        bot_management_usecase = _get_bot_management_usecase()
        bot_info = bot_management_usecase.get_bot_info_by_name(name)
        if not bot_info:
            return jsonify({"error": f"Bot not found: {name}"}), 404

        trading_usecase = _get_trading_usecase()
        trading_usecase.force_sell(bot_info, sell_ratio)

        return jsonify({"message": f"{name} {sell_ratio}% sold"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ===== 텔레그램 메시지 전송 라우트 =====

def _get_message_jobs():
    """MessageJobs 의존성 주입"""
    deps = get_dependencies()
    portfolio_usecase = _get_portfolio_usecase()
    return MessageJobs(
        portfolio_usecase=portfolio_usecase,
        message_repo=deps.message_repo
    )


@trade_bp.route('/send_trade_status', methods=['POST'])
@require_web_auth
def send_trade_status():
    """거래 상태 메시지 전송"""
    print("\n" + "=" * 80)
    print("🔔 /send_trade_status 엔드포인트 호출됨")
    print("=" * 80)

    try:
        message_jobs = _get_message_jobs()
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
        deps = get_dependencies()
        deps.message_repo.send_message("Failed to send Trade Status.")
        return jsonify({'error': '거래 상태 메시지 전송 실패'}), 500


@trade_bp.route('/send_history_status', methods=['POST'])
@require_web_auth
def send_history_status():
    """거래 기록 메시지 전송"""
    print("\n" + "=" * 80)
    print("🔔 /send_history_status 엔드포인트 호출됨")
    print("=" * 80)

    try:
        message_jobs = _get_message_jobs()
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
        deps = get_dependencies()
        deps.message_repo.send_message("Failed to send History Status.")
        return jsonify({'error': '거래 기록 메시지 전송 실패'}), 500
