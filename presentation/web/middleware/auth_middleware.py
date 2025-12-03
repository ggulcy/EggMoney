"""Flask 인증 미들웨어"""
import os
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
from typing import Callable, Any

from config.item import is_test


def require_api_key(f: Callable) -> Callable:
    """
    API 키 인증 데코레이터 (API 엔드포인트용)

    - is_test=True: 테스트 모드, 인증 우회
    - is_test=False: 운영 모드, 환경변수 API_KEY 검증 필수
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # 운영 모드: 환경변수에서 API 키 검증
        api_key = os.getenv('API_KEY')
        if not api_key:
            return jsonify({
                "success": False,
                "error": "서버 설정 오류: API_KEY가 설정되지 않았습니다."
            }), 500

        request_api_key = request.headers.get('X-API-Key')
        if not request_api_key or request_api_key != api_key:
            return jsonify({
                "success": False,
                "error": "인증이 필요합니다."
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def require_web_auth(f: Callable) -> Callable:
    """
    세션 기반 웹 인증 데코레이터 (웹 페이지용)

    - is_test=True: 테스트 모드, 인증 우회
    - is_test=False: 운영 모드, 세션 또는 API 키 검증
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # 세션에 인증 정보가 있는지 확인
        if session.get('authenticated'):
            return f(*args, **kwargs)

        # API 키로도 인증 가능 (API 호출용)
        api_key = os.getenv('API_KEY')
        if api_key:
            request_api_key = request.headers.get('X-API-Key')
            if request_api_key and request_api_key == api_key:
                return f(*args, **kwargs)

        # 인증되지 않은 경우 로그인 페이지로 리다이렉트
        return redirect(url_for('index.index'))

    return decorated_function
