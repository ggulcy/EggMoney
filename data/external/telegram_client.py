"""Telegram 클라이언트 - 메시지 및 사진 전송"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from telegram import Bot
from telegram.request import HTTPXRequest
from telegram.error import TimedOut, NetworkError

from config import is_test


def _get_bot_config() -> tuple[str, str]:
    """
    환경변수에서 Telegram Bot 설정 반환

    Returns:
        tuple[bot_token, chat_id]
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수가 필요합니다.")

    return bot_token, chat_id


async def _send_message_async(message: str, photo_path: Optional[str] = None) -> None:
    """
    Telegram 봇을 사용하여 비동기로 메시지 전송 (사진 선택적)

    Args:
        message: 전송할 메시지
        photo_path: 전송할 사진 경로 (선택적, 상대 경로 가능)

    Raises:
        Exception: 최대 재시도 횟수 초과 시
    """
    max_retries = 3
    retry_delay = 10  # 10초

    # Bot 설정
    bot_token, chat_id = _get_bot_config()

    # Bot 객체 생성 (타임아웃 설정)
    bot = Bot(
        token=bot_token,
        request=HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30.0,
            read_timeout=30.0
        )
    )

    # 로그 출력
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if photo_path:
        print(f"📸 [{now_str}] 텔레그램 메시지 (사진 포함): {message}")
    else:
        print(f"📱 [{now_str}] 텔레그램 메시지: {message}")

    # 사진 경로 처리
    absolute_photo_path = None
    if photo_path:
        # 상대 경로를 절대 경로로 변환
        if not os.path.isabs(photo_path):
            script_dir = Path(__file__).parent
            absolute_photo_path = script_dir / photo_path
        else:
            absolute_photo_path = Path(photo_path)

        # 파일 존재 확인
        if not absolute_photo_path.exists():
            print(f"⚠️ 사진 파일을 찾을 수 없음: {absolute_photo_path}")
            absolute_photo_path = None

    # 재시도 로직
    for attempt in range(max_retries):
        try:
            if not is_test:
                if absolute_photo_path:
                    # 사진과 함께 전송
                    with open(absolute_photo_path, 'rb') as photo:
                        await bot.send_photo(chat_id=chat_id, photo=photo, caption=message)
                    print(f"✅ 사진+메시지 전송 성공")
                else:
                    # 텍스트만 전송
                    await bot.send_message(chat_id=chat_id, text=message)
                    print(f"✅ 메시지 전송 성공")

            print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n")
            return

        except (TimedOut, NetworkError) as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 텔레그램 전송 실패 (시도 {attempt + 1}/{max_retries}). {retry_delay}초 후 재시도...")
                print(f"에러: {str(e)}")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ 모든 재시도 실패. 최종 에러: {str(e)}")
                raise

        except Exception as e:
            print(f"⚠️ 예기치 못한 오류 발생: {str(e)}")
            raise


def send_message_sync(message: str, photo_path: Optional[str] = None) -> None:
    """
    Telegram 메시지를 동기적으로 전송 (사진 선택적)

    Args:
        message: 전송할 메시지
        photo_path: 전송할 사진 경로 (선택적)
            - None: 텍스트 메시지만 전송
            - 경로 지정: 사진과 함께 전송 (상대/절대 경로 모두 지원)

    Examples:
        >>> send_message_sync("일반 메시지")
        >>> send_message_sync("수익 달성!", "pepe_glass.png")
        >>> send_message_sync("경고 메시지", "/path/to/warning.png")
    """
    try:
        if not message:
            return

        asyncio.run(_send_message_async(message, photo_path))

    except Exception as e:
        print(f"💥 텔레그램 전송 실패: {str(e)}")
        print(f"💥 프로그램은 계속 실행됩니다")
