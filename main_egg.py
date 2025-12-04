"""
EggMoney - 기술지표 기반 자동 매매 시스템
Flask 애플리케이션 진입점

ValueRebalancing 스타일로 간소화:
- create_app(): Flask 앱 생성
- set_scheduler(): 스케줄러 설정 (모든 로직은 scheduler_config 내부에서 처리)
- main(): 애플리케이션 시작
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일은 config.item에서 로드됨
from flask import Flask, render_template
from config.item import is_test, admin, BotAdmin

# 환경 설정
HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT'))


def create_app():
    """
    Flask 애플리케이션 생성

    Returns:
        Flask 애플리케이션 인스턴스
    """
    from datetime import timedelta

    app = Flask(
        __name__,
        template_folder='presentation/web/templates',
        static_folder='presentation/web/static',
        static_url_path='/static'
    )

    # 시크릿 키 설정 (CSRF 보호 및 세션 암호화)
    app.secret_key = os.getenv('SECRET_KEY')

    # 세션 설정 (2시간 동안 유지)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

    # 블루프린트 등록
    from presentation.web.routes import bot_info_bp, status_bp, index_bp, trade_bp, auth_bp
    import presentation.web.routes.bot_info_routes
    import presentation.web.routes.trade_routes

    app.register_blueprint(auth_bp)
    app.register_blueprint(index_bp)
    app.register_blueprint(bot_info_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(trade_bp)

    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        """404 Not Found 에러 핸들러"""
        return "<h1>404 Not Found</h1><p>페이지를 찾을 수 없습니다.</p>", 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error 핸들러"""
        return "<h1>500 Internal Server Error</h1><p>서버 오류가 발생했습니다.</p>", 500

    return app


def set_scheduler():
    """
    스케줄러 설정 및 시작

    모든 초기화 로직은 scheduler_config.start_scheduler() 내부에서 처리됩니다.
    - Dependencies 초기화 (SessionFactory, Repository, Usecase, Jobs)
    - 스케줄 시간 설정
    - 초기화 작업 (메시지, CSV, 봇 sync)
    - APScheduler 작업 등록 및 시작
    """
    try:
        from presentation.scheduler.scheduler_config import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"⚠️ 스케줄러 초기화 실패: {str(e)}")
        print("웹 서버만 실행됩니다.")
        import traceback
        traceback.print_exc()


def main():
    """애플리케이션 시작"""
    print("=" * 80)
    print("🚀 EggMoney 애플리케이션 시작")
    print("=" * 80)
    print(f"📍 Host: {HOST}")
    print(f"📍 Port: {PORT}")
    print(f"📍 Test Mode: {is_test}")
    print(f"📍 Admin: {admin}")
    print("=" * 80)

    # Flask 앱 생성
    app = create_app()

    # 프로덕션 모드에서만 스케줄러 시작
    if not is_test:
        set_scheduler()
    else:
        print("🧪 TEST 모드입니다. 스케줄러를 시작하지 않습니다.")

    # Flask 서버 실행
    print(f"\n🌐 Flask 서버 시작...\n")
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == '__main__':
    main()
