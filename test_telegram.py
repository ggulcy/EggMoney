"""Telegram 클라이언트 테스트"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.external.telegram_client import send_message_sync

if __name__ == "__main__":
    print("=" * 80)
    print("📱 Telegram Client Test")
    print("=" * 80)

    # 테스트 1: 일반 텍스트 메시지
    print("\n[테스트 1] 일반 텍스트 메시지")
    send_message_sync("🧪 EggMoney 텔레그램 테스트 - 일반 메시지")

    # 테스트 2: 사진 + 메시지
    print("\n[테스트 2] 사진 + 메시지")
    send_message_sync("🧪 EggMoney 텔레그램 테스트 - 사진 포함 🎉", "pepe_glass.png")

    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
