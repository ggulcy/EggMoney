# -*- coding: utf-8 -*-
"""한국투자증권 API 클라이언트"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

import requests

from config import key_store
from data.external.hantoo.hantoo_models import HantooExd

# 로거 설정
logging.basicConfig(
    level=logging.DEBUG,
    filename='app.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class HantooAccountInfo:
    """한국투자증권 계좌 정보 (환경변수에서 로드)"""

    def __init__(self):
        """환경변수에서 계좌 정보 초기화"""
        self.cano = os.getenv('HANTOO_CANO')
        self.acnt_prdt_cd = os.getenv('HANTOO_ACNT_PRDT_CD', '01')
        self.api_url = os.getenv('HANTOO_API_URL', 'https://openapi.koreainvestment.com:9443')
        self.app_key = os.getenv('HANTOO_APP_KEY')
        self.app_secret = os.getenv('HANTOO_APP_SECRET')

        if not self.cano or not self.app_key or not self.app_secret:
            raise ValueError("HANTOO_CANO, HANTOO_APP_KEY, HANTOO_APP_SECRET 환경변수가 필요합니다.")


class HantooClient:
    """한국투자증권 API 클라이언트"""

    # 거래소 코드 매핑 테이블
    EXCHANGE_TABLE = {
        "SOXL": ("AMEX", "AMS"),
        "TQQQ": ("NASD", "NAS"),
        "QQQ": ("NASD", "NAS"),
        "BULZ": ("AMEX", "AMS"),
        "UPRO": ("AMEX", "AMS"),
        "LABU": ("AMEX", "AMS"),
        "RETL": ("AMEX", "AMS"),
        "FAS": ("AMEX", "AMS"),
        "ERX": ("AMEX", "AMS"),
        "CURE": ("AMEX", "AMS"),
        "DRN": ("AMEX", "AMS"),
        "WANT": ("AMEX", "AMS"),
        "TECL": ("AMEX", "AMS"),
        "TPOR": ("AMEX", "AMS"),
        "UTSL": ("AMEX", "AMS"),
        "BITU": ("AMEX", "AMS"),
    }

    def __init__(self):
        """한국투자증권 클라이언트 초기화"""
        self.account_info = HantooAccountInfo()

    def get_hantoo_exd(self, symbol: str) -> HantooExd:
        """
        종목 심볼을 기준으로 한투 거래소 코드 조회

        Args:
            symbol: 종목 심볼 (예: TQQQ, SOXL)

        Returns:
            HantooExd: 거래소 정보 (기본값: AMEX/AMS)
        """
        if symbol in self.EXCHANGE_TABLE:
            trading_exd, price_exd = self.EXCHANGE_TABLE[symbol]
            return HantooExd(trading_exd=trading_exd, price_exd=price_exd)
        # 기본값: AMEX/AMS
        return HantooExd(trading_exd="AMEX", price_exd="AMS")

    def _request_token(self) -> requests.Response:
        """
        토큰 발급 요청

        Returns:
            requests.Response: API 응답
        """
        url = self.account_info.api_url + "/oauth2/tokenP"
        headers = {
            "Content-Type": "application/json; charset=UTF-8"
        }
        body = {
            "grant_type": "client_credentials",
            "appkey": self.account_info.app_key,
            "appsecret": self.account_info.app_secret
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            msg = f"POST {url} - Status: {response.status_code}"
            logging.debug(msg)
            print(msg)
            return response
        except requests.exceptions.RequestException as e:
            msg = f"POST Request Failed: {e}"
            logging.error(msg)
            raise

    def _update_token(self) -> Optional[str]:
        """
        토큰 갱신 (새로운 토큰 발급)

        Returns:
            Optional[str]: 발급된 토큰, 실패 시 None
        """
        response = self._request_token()

        if response.status_code == 200:
            try:
                response_data = response.json()
                access_token = response_data.get('access_token')
                expiration = response_data.get('access_token_token_expired')

                # key_store에 저장
                key_store.write(key_store.AT_KEY, access_token)
                key_store.write(key_store.AT_EX_DATE, expiration)

                print(f"✅ 새로운 토큰 발급 완료 (만료일: {expiration})")
                logging.info(f"새로운 토큰 발급 완료 (만료일: {expiration})")

                return access_token
            except json.JSONDecodeError:
                logging.error("JSON 응답 파싱 실패")
                return None

        elif response.status_code == 403:
            try:
                response_data = response.json()
                error_code = response_data.get('error_code')
                if error_code == "EGW00133":
                    print("토큰 발급 횟수 초과, 65초 대기 후 재시도합니다")
                    logging.info("토큰 발급 횟수 초과, 65초 대기 후 재시도합니다")
                    time.sleep(65)
                    return self._update_token()
                else:
                    logging.error("알 수 없는 403 에러: 응답 내용 확인 필요")
            except json.JSONDecodeError:
                logging.error("JSON 응답 파싱 실패")
        else:
            logging.error(f"HTTP Error: {response.status_code}")
            logging.error(response.text)

        return None

    def _is_token_expired_error(self, response: requests.Response) -> bool:
        """토큰 만료 에러인지 확인 (EGW00123)"""
        if response.status_code in [401, 500]:
            try:
                data = response.json()
                if data.get("msg_cd") == "EGW00123":
                    return True
            except json.JSONDecodeError:
                pass
        return False

    def _get_token(self) -> str:
        """
        유효한 토큰 조회 (만료 시 갱신)
        - 매번 key_store에서 읽어서 최신 토큰 사용

        Returns:
            str: 유효한 토큰
        """
        # 매번 key_store에서 토큰과 만료일 읽기 (egg 프로젝트 방식)
        token = key_store.read(key_store.AT_KEY)
        token_expiration = key_store.read(key_store.AT_EX_DATE)

        # [DEBUG] 토큰 상태 로깅
        token_preview = token[:20] + "..." if token else None
        print(f"\n[DEBUG] _get_token() 호출")
        print(f"[DEBUG] 토큰 존재 여부: {token is not None} (preview: {token_preview})")
        print(f"[DEBUG] 만료일 존재 여부: {token_expiration is not None} (value: {token_expiration})")
        logging.info(f"[DEBUG] 토큰={token is not None}, 만료일={token_expiration}")

        # 토큰이 없으면 새로 발급
        if token is None:
            logging.info("토큰이 없습니다. 토큰을 발급합니다.")
            print("[DEBUG] ❌ 토큰이 없습니다. 토큰을 발급합니다.")
            return self._update_token()

        # 토큰 만료 여부 체크
        if token_expiration:
            try:
                expiration_datetime = datetime.strptime(token_expiration, "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()

                # 만료 1시간 전에 갱신 (egg 프로젝트 방식)
                from datetime import timedelta
                expiration_with_buffer = expiration_datetime - timedelta(hours=1)

                # [DEBUG] 시간 비교 로깅
                print(f"[DEBUG] 현재 시간: {current_time}")
                print(f"[DEBUG] 만료 시간: {expiration_datetime}")
                print(f"[DEBUG] 만료 1시간 전: {expiration_with_buffer}")
                print(f"[DEBUG] 토큰 유효 여부: {current_time < expiration_with_buffer}")
                logging.info(f"[DEBUG] 현재={current_time}, 만료={expiration_datetime}, 유효={current_time < expiration_with_buffer}")

                if current_time < expiration_with_buffer:
                    print(f"[DEBUG] ✅ 토큰 유효 (만료까지 {expiration_with_buffer - current_time} 남음)")
                    return token
                else:
                    logging.info("토큰이 만료되었습니다. 새로운 토큰을 발급합니다.")
                    print(f"[DEBUG] ⏰ 토큰이 만료 1시간 전입니다. 새로운 토큰을 발급합니다.")
                    return self._update_token()
            except ValueError as e:
                logging.error(f"유효하지 않은 만료일 형식입니다: {e}")
                print(f"[DEBUG] ❌ 유효하지 않은 만료일 형식입니다: {e}")
                return self._update_token()
        else:
            logging.warning("유효하지 않은 만료일 정보입니다. 새로운 토큰을 발급합니다.")
            print("[DEBUG] ❌ 유효하지 않은 만료일 정보입니다. 새로운 토큰을 발급합니다.")
            return self._update_token()

    def post_request(
        self,
        end_point_url: str,
        extra_headers: Optional[Dict[str, str]] = None,
        extra_body: Optional[Dict[str, str]] = None,
        _retry: bool = False
    ) -> requests.Response:
        """
        POST 요청 전송

        Args:
            end_point_url: API 엔드포인트
            extra_headers: 추가 헤더
            extra_body: 추가 바디
            _retry: 재시도 여부 (내부 사용)

        Returns:
            requests.Response: API 응답
        """
        url = self.account_info.api_url + end_point_url
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": "Bearer " + self._get_token(),
            "appkey": self.account_info.app_key,
            "appsecret": self.account_info.app_secret
        }
        if extra_headers:
            headers.update(extra_headers)

        body = {
            "CANO": self.account_info.cano,
            "ACNT_PRDT_CD": self.account_info.acnt_prdt_cd
        }
        if extra_body:
            body.update(extra_body)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            msg = f"POST {url} - Status: {response.status_code}"
            logging.debug(msg)
            print(msg)

            # 토큰 만료 에러 시 갱신 후 재시도 (1회만)
            if not _retry and self._is_token_expired_error(response):
                print("🔄 토큰 만료 감지, 갱신 후 재시도...")
                logging.info("토큰 만료 감지, 갱신 후 재시도")
                self._update_token()
                return self.post_request(end_point_url, extra_headers, extra_body, _retry=True)

            # 에러 응답 시 본문 출력
            if response.status_code >= 400:
                print(f"❌ Response Body: {response.text}")
                logging.error(f"Response Body: {response.text}")
            return response
        except requests.exceptions.RequestException as e:
            msg = f"POST Request Failed: {e}"
            logging.error(msg)
            raise

    def get_request(
        self,
        end_point: str,
        extra_header: Optional[Dict[str, str]] = None,
        extra_param: Optional[Dict[str, str]] = None,
        _retry: bool = False
    ) -> requests.Response:
        """
        GET 요청 전송

        Args:
            end_point: API 엔드포인트
            extra_header: 추가 헤더
            extra_param: URL 쿼리 파라미터
            _retry: 재시도 여부 (내부 사용)

        Returns:
            requests.Response: API 응답
        """
        url = self.account_info.api_url + end_point
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": "Bearer " + self._get_token(),
            "appkey": self.account_info.app_key,
            "appsecret": self.account_info.app_secret
        }
        if extra_header:
            headers.update(extra_header)

        # 기본 쿼리 파라미터 설정
        default_query_params = {
            "CANO": self.account_info.cano,
            "ACNT_PRDT_CD": self.account_info.acnt_prdt_cd
        }

        if extra_param:
            default_query_params.update(extra_param)

        try:
            response = requests.get(url, headers=headers, params=default_query_params)
            msg = f"GET {url} - Status: {response.status_code}"
            logging.debug(msg)
            print(msg)

            # 토큰 만료 에러 시 갱신 후 재시도 (1회만)
            if not _retry and self._is_token_expired_error(response):
                print("🔄 토큰 만료 감지, 갱신 후 재시도...")
                logging.info("토큰 만료 감지, 갱신 후 재시도")
                self._update_token()
                return self.get_request(end_point, extra_header, extra_param, _retry=True)

            # 에러 응답 시 본문 출력
            if response.status_code >= 400:
                print(f"❌ Response Body: {response.text}")
                logging.error(f"Response Body: {response.text}")
            return response
        except requests.exceptions.RequestException as e:
            msg = f"GET Request Failed: {e}"
            logging.error(msg)
            raise
