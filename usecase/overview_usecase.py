"""Overview Usecase - Overview 서버 연동"""
import requests
from typing import Optional, Dict, Any

from config.item import admin, is_test


class OverviewUsecase:
    """Overview 서버 연동 Usecase"""

    def __init__(self):
        """
        Overview Usecase 초기화

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

    def get_deposit_info(self) -> Optional[Dict[str, Any]]:
        """
        Overview 서버에서 입출금 정보 조회

        owner: admin.value (chan, choe 등)
        project: EggMoney (하드코딩)

        Returns:
            Dict: 입출금 정보
                {
                    "status": "ok",
                    "owner": "chan",
                    "project": "EggMoney",
                    "data": {
                        "deposit_krw": 원화 입금 합계,
                        "withdraw_krw": 원화 출금 합계,
                        "deposit_usd": 달러 입금 합계,
                        "withdraw_usd": 달러 출금 합계,
                        "net_deposit_krw": 원화 순입금,
                        "net_deposit_usd": 달러 순입금
                    }
                }
            또는 None (실패 시)
        """
        if not self.base_url:
            print("❌ admin이 설정되지 않아 Overview 서버 주소를 알 수 없습니다.")
            return None

        if not admin:
            print("❌ admin이 설정되지 않았습니다.")
            return None

        owner = admin.value
        project = "EggMoney"

        try:
            url = f"{self.base_url}/api/external/deposit"
            params = {
                "owner": owner,
                "project": project
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "ok":
                print(f"✅ Overview 입출금 정보 조회 성공: {owner}/{project}")
                return data
            else:
                print(f"❌ Overview API 오류: {data.get('message', 'Unknown error')}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Overview 서버 연결 실패: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Overview 입출금 정보 조회 실패: {str(e)}")
            return None
