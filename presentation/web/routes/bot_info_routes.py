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
        market_state_level = key_store.read(key_store.MARKET_STATE_LEVEL)
        total_budget = key_store.read(key_store.TOTAL_BUDGET)
        auto_start = key_store.read(key_store.AUTO_START)

        return render_template('bot_info.html',
                               bot_info_with_tiers=bot_info_with_tiers,
                               bot_infos=all_bots,
                               trade_time=trade_time,
                               PointLoc=PointLoc,
                               twap_time=twap_time,
                               twap_count=twap_count,
                               market_state_level=market_state_level,
                               saved_total_budget=total_budget,
                               auto_start=auto_start)
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
        point_loc_value = data.get('point_loc', 'P1')
        point_loc = PointLoc(point_loc_value)
        dynamic_seed_max = float(data.get('dynamic_seed_max', 0))
        dynamic_seed_enabled = data.get('dynamic_seed_enabled', False)
        dynamic_seed_multiplier = float(data.get('dynamic_seed_multiplier', 1.3))
        dynamic_seed_t_threshold = float(data.get('dynamic_seed_t_threshold', 0.3))
        dynamic_seed_drop_rate = float(data.get('dynamic_seed_drop_rate', 0.03))
        added_seed = float(data.get('added_seed', 0))

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
            point_loc=point_loc,
            added_seed=added_seed,
            dynamic_seed_max=dynamic_seed_max,
            dynamic_seed_enabled=dynamic_seed_enabled,
            dynamic_seed_multiplier=dynamic_seed_multiplier,
            dynamic_seed_t_threshold=dynamic_seed_t_threshold,
            dynamic_seed_drop_rate=dynamic_seed_drop_rate,
        )
        bot_management_usecase.update_bot_info(bot_info)

        # 수동 설정 변경 시 시장 레벨을 -1(수동설정)으로 변경
        key_store.write(key_store.MARKET_STATE_LEVEL, -1)

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
    """모든 설정을 한 번에 저장 (Trade Start, Trade End, TWAP Count, Auto Start)"""
    try:
        data = request.get_json()

        # Trade Start, Trade End, TWAP Count, Auto Start 설정
        trade_start = data.get('trade_start')
        trade_end = data.get('trade_end')
        twap_count = data.get('twap_count')
        auto_start = data.get('auto_start', False)

        # 필수 필드 검증
        if not trade_start or not trade_end or not twap_count:
            return jsonify({"error": "All time fields required"}), 400

        # TWAP Start 계산 (Trade Start + 5분)
        from datetime import datetime, timedelta
        trade_start_time = datetime.strptime(trade_start, "%H:%M")
        twap_start_time = trade_start_time + timedelta(minutes=5)
        twap_start = twap_start_time.strftime("%H:%M")

        # 저장
        key_store.write(key_store.TRADE_TIME, trade_start)  # TRADE_TIME에 trade_start 저장
        key_store.write(key_store.TWAP_TIME, [twap_start, trade_end])  # TWAP_TIME에 [자동계산된 start, 사용자입력 end]
        key_store.write(key_store.TWAP_COUNT, int(twap_count))
        key_store.write(key_store.AUTO_START, auto_start)  # AUTO_START 저장

        # 스케줄러 재시작
        start_scheduler()

        return jsonify({"message": "All settings saved"}), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/preview_bot_renewal', methods=['POST'])
def preview_bot_renewal():
    """시장 단계에 따른 봇 리뉴얼 미리보기"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        market_stage = data.get('market_stage')
        total_budget = data.get('total_budget')  # 사용자 지정 총 예산 (선택사항)

        if market_stage is None:
            return jsonify({"error": "market_stage required"}), 400

        # 시장 단계 유효성 검증
        if market_stage not in [0, 1, 2, 3]:
            return jsonify({"error": "Invalid market_stage (must be 0-3)"}), 400

        # 총 예산 유효성 검증 (있는 경우)
        if total_budget is not None:
            if not isinstance(total_budget, (int, float)) or total_budget <= 0:
                return jsonify({"error": "Invalid total_budget (must be positive number)"}), 400

        # 봇 리뉴얼 미리보기
        preview = bot_management_usecase.preview_bot_renewal(market_stage, custom_total_budget=total_budget)

        return jsonify(preview), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bot_info_bp.route('/apply_bot_renewal', methods=['POST'])
@require_web_auth
def apply_bot_renewal():
    """시장 단계에 따른 봇 리뉴얼 적용"""
    bot_management_usecase = _get_dependencies()
    try:
        data = request.get_json()
        market_stage = data.get('market_stage')
        total_budget = data.get('total_budget')  # 사용자 지정 총 예산 (선택사항)

        if market_stage is None:
            return jsonify({"error": "market_stage required"}), 400

        # 시장 단계 유효성 검증
        if market_stage not in [0, 1, 2, 3]:
            return jsonify({"error": "Invalid market_stage (must be 0-3)"}), 400

        # 총 예산 유효성 검증 (있는 경우)
        if total_budget is not None:
            if not isinstance(total_budget, (int, float)) or total_budget <= 0:
                return jsonify({"error": "Invalid total_budget (must be positive number)"}), 400

        # 봇 리뉴얼 적용
        result = bot_management_usecase.apply_bot_renewal(market_stage, custom_total_budget=total_budget)

        # 시장 단계 저장
        key_store.write(key_store.MARKET_STATE_LEVEL, market_stage)

        # 총 예산 저장 (사용자가 지정한 경우)
        if total_budget is not None:
            key_store.write(key_store.TOTAL_BUDGET, total_budget)

        return jsonify({
            "message": "Bot renewal applied successfully",
            "updated_count": result["updated_count"],
            "market_stage": market_stage
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
