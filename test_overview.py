"""Overview Usecase 테스트"""
import sys
sys.path.insert(0, '/Users/chanhypark/workspace/private/python/EggMoney')

from usecase.overview_usecase import OverviewUsecase


def main():
    print("=" * 60)
    print("Overview Usecase 테스트")
    print("=" * 60)

    usecase = OverviewUsecase()
    print(f"서버 주소: {usecase.service.client.base_url}")
    print()

    result = usecase.get_deposit_info()

    if result:
        print("\n" + "-" * 60)
        print("조회 결과:")
        print("-" * 60)
        print(f"  Owner: {result.get('owner')}")
        print(f"  Project: {result.get('project')}")

        data = result.get('data', {})
        print(f"\n  입금 (KRW): ₩{data.get('deposit_krw', 0):,.0f}")
        print(f"  출금 (KRW): ₩{data.get('withdraw_krw', 0):,.0f}")
        print(f"  순입금 (KRW): ₩{data.get('net_deposit_krw', 0):,.0f}")
        print()
        print(f"  입금 (USD): ${data.get('deposit_usd', 0):,.2f}")
        print(f"  출금 (USD): ${data.get('withdraw_usd', 0):,.2f}")
        print(f"  순입금 (USD): ${data.get('net_deposit_usd', 0):,.2f}")
    else:
        print("\n❌ 조회 실패")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
