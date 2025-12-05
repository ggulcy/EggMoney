"""인증 관리 라우트"""
import os
from flask import Blueprint, request, jsonify, session, redirect, url_for, Response
from typing import Tuple, Union

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login() -> tuple[Response, int]:
    """
    로그인 처리

    Request Body (JSON):
        {
            "password": str (비밀번호)
        }

    환경변수 API_KEY와 비교하여 일치하면 세션에 인증 정보 저장
    """
    try:
        data = request.get_json()

        if not data or 'password' not in data:
            return jsonify({
                "success": False,
                "error": "비밀번호를 입력해주세요."
            }), 400

        password = data.get('password')
        api_key = os.getenv('API_KEY')

        # 디버깅: 환경변수 확인
        print(f"🔍 환경변수 API_KEY 존재 여부: {api_key is not None}")

        if not api_key:
            return jsonify({
                "success": False,
                "error": "서버 설정 오류: API_KEY가 설정되지 않았습니다."
            }), 500

        # 비밀번호와 API_KEY 비교
        if password == api_key:
            # 세션에 인증 정보 저장
            session['authenticated'] = True
            session.permanent = True  # 영구 세션 (브라우저 닫아도 유지)

            return jsonify({
                "success": True,
                "message": "로그인 성공"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "비밀번호가 일치하지 않습니다."
            }), 401

    except Exception as e:
        print(f"❌ 로그인 처리 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"로그인 실패: {str(e)}"
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout() -> tuple[Response, int]:
    """
    로그아웃 처리

    세션에서 인증 정보 제거
    """
    session.pop('authenticated', None)
    return jsonify({
        "success": True,
        "message": "로그아웃 성공"
    }), 200


@auth_bp.route('/check_auth', methods=['GET'])
def check_auth() -> tuple[Response, int]:
    """
    인증 상태 확인

    Returns:
        {"authenticated": bool}
    """
    return jsonify({
        "authenticated": session.get('authenticated', False)
    }), 200
