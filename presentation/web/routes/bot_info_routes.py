from flask import render_template, request, jsonify
from config import key_store
from config.dependencies import get_dependencies
from usecase import BotManagementUsecase
from domain.value_objects import PointLoc
from domain.entities import BotInfo
from presentation.scheduler.scheduler_config import start_scheduler
from presentation.web.middleware.auth_middleware import require_web_auth

from presentation.web.routes import bot_info_bp


def _get_dependencies():
    """DI 컨테이너에서 의존성을 조회하여 Usecase 생성"""
    deps = get_dependencies()

    bot_management_usecase = BotManagementUsecase(
        bot_info_repo=deps.bot_info_repo,
        trade_repo=deps.trade_repo,
        exchange_repo=deps.exchange_repo,
        message_repo=deps.message_repo,
    )
    return bot_management_usecase


@bot_info_bp.route('/bot_info', methods=['GET'])
def bot_info_template():
    bot_management_usecase = _get_dependencies()
    try:
        bot_data = bot_management_usecase.get_all_bot_info_with_t()
        bot_info_with_tiers = [(item['bot_info'], item['t']) for item in bot_data]
        all_bots = [item['bot_info'] for item in bot_data]

        trade_time = key_store.read(key_store.TRADE_TIME) or "04:35"
        twap_time = key_store.read(key_store.TWAP_TIME) or ["04:40", "09:00"]
        twap_count = key_store.read(key_store.TWAP_COUNT) or 5
        auto_start = key_store.read(key_store.AUTO_START)
        auto_start_threshold = key_store.read(key_store.AUTO_START_THRESHOLD)
        closing_buy_time = key_store.read(key_store.CLOSING_BUY_TIME)
        total_budget = key_store.read(key_store.TOTAL_BUDGET)

        return render_template('bot_info.html',
                               bot_info_with_tiers=bot_info_with_tiers,
                               bot_infos=all_bots,
                               trade_time=trade_time,
                               PointLoc=PointLoc,
                               twap_time=twap_time,
                               twap_count=twap_count,
                               auto_start=auto_start,
                               auto_start_threshold=auto_start_threshold,
                               closing_buy_time=closing_buy_time,
                               saved_total_budget=total_budget)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/save_bot_info', methods=['POST'])
@require_web_auth
def save_bot_info():
    """개별 bot_info 저장/업데이트"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name')
        symbol = data.get('symbol')
        seed = float(data.get('seed', 0))
        max_tier = int(data.get('max_tier', 0))
        profit_rate = float(data.get('profit_rate', 0))
        t_div = int(data.get('t_div', 0))
        is_check_buy_avr_price = data.get('is_check_buy_avr_price', False)
        is_check_buy_t_div_price = data.get('is_check_buy_t_div_price', False)
        active = data.get('active', False)
        skip_sell = data.get('skip_sell', False)
        sell_cooldown_days = int(data.get('sell_cooldown_days', 0))
        sell_cooldown_loss_only = data.get('sell_cooldown_loss_only', False)
        point_loc_value = data.get('point_loc', 'P1')
        point_loc = PointLoc(point_loc_value)
        added_seed = float(data.get('added_seed', 0))
        closing_buy_conditions = data.get('closing_buy_conditions', [])
        trailing_enabled = data.get('trailing_enabled', False)
        trailing_t_threshold = float(data.get('trailing_t_threshold', 0.3))
        trailing_atr_multiplier = float(data.get('trailing_atr_multiplier', 1.0))
        trailing_floor_rate = float(data.get('trailing_floor_rate', 0.10))

        # 기존 봇 상태 유지 (trailing_mode, high_watermark, trailing_stop은 로직에서만 변경)
        existing = bot_management_usecase.get_bot_info_by_name(name)
        trailing_mode = existing.trailing_mode if existing else False
        trailing_high_watermark = existing.trailing_high_watermark if existing else 0.0
        trailing_stop = existing.trailing_stop if existing else 0.0

        bot_info = BotInfo(
            name=name,
            symbol=symbol,
            seed=seed,
            max_tier=max_tier,
            profit_rate=profit_rate,
            t_div=t_div,
            is_check_buy_avr_price=is_check_buy_avr_price,
            is_check_buy_t_div_price=is_check_buy_t_div_price,
            active=active,
            skip_sell=skip_sell,
            sell_cooldown_days=sell_cooldown_days,
            sell_cooldown_loss_only=sell_cooldown_loss_only,
            point_loc=point_loc,
            added_seed=added_seed,
            closing_buy_conditions=closing_buy_conditions,
            trailing_enabled=trailing_enabled,
            trailing_t_threshold=trailing_t_threshold,
            trailing_atr_multiplier=trailing_atr_multiplier,
            trailing_floor_rate=trailing_floor_rate,
            trailing_mode=trailing_mode,
            trailing_high_watermark=trailing_high_watermark,
            trailing_stop=trailing_stop,
        )
        bot_management_usecase.update_bot_info(bot_info)

        return jsonify({"message": f"{name} saved"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/delete_bot_info', methods=['POST'])
@require_web_auth
def delete_bot_info():
    """개별 bot_info 삭제"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({"error": "Name required"}), 400
        bot_management_usecase.delete_bot_info(name)
        return jsonify({"message": f"{name} deleted"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/add_bot_info', methods=['POST'])
@require_web_auth
def add_bot_info():
    """새로운 bot_info 추가"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        name = data.get('name')
        symbol = data.get('symbol', '')
        seed = float(data.get('seed', 1))
        max_tier = int(data.get('max_tier', 0))
        profit_rate = float(data.get('profit_rate', 0))
        t_div = int(data.get('t_div', 0))

        if not name:
            return jsonify({"error": "Name required"}), 400

        # 중복 체크
        existing = bot_management_usecase.get_bot_info_by_name(name)
        if existing:
            return jsonify({"error": f"{name} already exists"}), 400

        bot_info = BotInfo(
            name=name,
            symbol=symbol,
            seed=seed,
            max_tier=max_tier,
            profit_rate=profit_rate,
            t_div=t_div,
            is_check_buy_avr_price=False,
            is_check_buy_t_div_price=False,
            active=True,
            skip_sell=False,
            point_loc=PointLoc.P1,
            added_seed=0,
        )
        bot_management_usecase.update_bot_info(bot_info)
        return jsonify({"message": f"{name} added"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/save_all_settings', methods=['POST'])
@require_web_auth
def save_all_settings():
    """스케줄 설정 저장 (Trade Start, Trade End, TWAP Count, Closing Buy Time)"""
    try:
        data = request.get_json()

        trade_start = data.get('trade_start')
        trade_end = data.get('trade_end')
        twap_count = data.get('twap_count')

        # 필수 필드 검증
        if not trade_start or not trade_end or not twap_count:
            return jsonify({"error": "All time fields required"}), 400

        # TWAP Start 계산 (Trade Start + 5분)
        from datetime import datetime, timedelta
        trade_start_time = datetime.strptime(trade_start, "%H:%M")
        twap_start_time = trade_start_time + timedelta(minutes=5)
        twap_start = twap_start_time.strftime("%H:%M")

        # 저장
        key_store.write(key_store.TRADE_TIME, trade_start)
        key_store.write(key_store.TWAP_TIME, [twap_start, trade_end])
        key_store.write(key_store.TWAP_COUNT, int(twap_count))

        # CLOSING_BUY_TIME 저장
        closing_buy_time = data.get('closing_buy_time')
        if closing_buy_time:
            key_store.write(key_store.CLOSING_BUY_TIME, closing_buy_time)

        # 스케줄러 재시작
        start_scheduler()

        return jsonify({"message": "All settings saved"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/save_other_settings', methods=['POST'])
@require_web_auth
def save_other_settings():
    """기타 설정 저장 (총자산, 자동 출발)"""
    try:
        data = request.get_json()

        total_budget = data.get('total_budget')
        auto_start = data.get('auto_start', False)
        auto_start_threshold = data.get('auto_start_threshold')

        # 총자산 저장
        if total_budget is not None and total_budget > 0:
            key_store.write(key_store.TOTAL_BUDGET, total_budget)

        # 자동 출발 저장
        key_store.write(key_store.AUTO_START, auto_start)

        # 자동 출발 임계 비율 저장
        if auto_start_threshold is not None:
            threshold = float(auto_start_threshold)
            if 0 < threshold <= 1:
                key_store.write(key_store.AUTO_START_THRESHOLD, threshold)

        return jsonify({"message": "Other settings saved"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/apply_bot_renewal', methods=['POST'])
@require_web_auth
def apply_bot_renewal():
    """봇 리뉴얼 적용 - 기존 봇 삭제 후 새로 생성"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        ticker_counts = data.get('ticker_counts')  # {"TQQQ": 2, "SOXL": 1}

        if not ticker_counts:
            return jsonify({"error": "ticker_counts required"}), 400

        total_budget = key_store.read(key_store.TOTAL_BUDGET)
        if not total_budget or total_budget <= 0:
            return jsonify({"error": "총자산을 먼저 설정해주세요."}), 400

        result = bot_management_usecase.apply_bot_renewal(ticker_counts, total_budget)

        return jsonify({
            "message": f"{result['created_count']}개 봇이 생성되었습니다.",
            "created_count": result["created_count"]
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


