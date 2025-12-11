# -*- coding: utf-8 -*-
"""Overview API 클라이언트"""
import logging
from typing import Dict, Optional

import requests

from config.item import admin, is_test

# 로거 설정
logging.basicConfig(
    level=logging.DEBUG,
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class OverviewClient:
    """Overview API 클라이언트 (HTTP 요청 담당)"""

    def __init__(self):
        """
        Overview 클라이언트 초기화

        서버 주소:
        - is_test=True: http://localhost:5001
        - is_test=False: https://{admin}.eggmoney.xyz
        """
        if is_test:
            self.base_url = "http://localhost:5001"
        elif admin:
            self.base_url = f"https://{admin.value}.eggmoney.xyz"
        else:
            self.base_url = None

    def get_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 10
    ) -> Optional[requests.Response]:
        """
        GET 요청 전송

        Args:
            endpoint: API 엔드포인트 (예: /api/external/deposit)
            params: URL 쿼리 파라미터
            timeout: 요청 타임아웃 (초)

        Returns:
            requests.Response: API 응답, 실패 시 None
        """
        if not self.base_url:
            logging.error("base_url이 설정되지 않았습니다.")
            return None

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=timeout)
            msg = f"GET {url} - Status: {response.status_code}"
            logging.debug(msg)
            print(msg)

            if response.status_code >= 400:
                print(f"Response Body: {response.text}")
                logging.error(f"Response Body: {response.text}")

            return response

        except requests.exceptions.RequestException as e:
            msg = f"GET Request Failed: {e}"
            logging.error(msg)
            print(f"Overview 서버 연결 실패: {e}")
            return None

    def post_request(
        self,
        endpoint: str,
        json_body: Optional[Dict] = None,
        timeout: int = 10
    ) -> Optional[requests.Response]:
        """
        POST 요청 전송

        Args:
            endpoint: API 엔드포인트
            json_body: JSON 바디
            timeout: 요청 타임아웃 (초)

        Returns:
            requests.Response: API 응답, 실패 시 None
        """
        if not self.base_url:
            logging.error("base_url이 설정되지 않았습니다.")
            return None

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.post(url, json=json_body, timeout=timeout)
            msg = f"POST {url} - Status: {response.status_code}"
            logging.debug(msg)
            print(msg)

            if response.status_code >= 400:
                print(f"Response Body: {response.text}")
                logging.error(f"Response Body: {response.text}")

            return response

        except requests.exceptions.RequestException as e:
            msg = f"POST Request Failed: {e}"
            logging.error(msg)
            print(f"Overview 서버 연결 실패: {e}")
            return None
