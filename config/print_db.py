"""DB 데이터 출력 유틸리티"""
import sys
from pathlib import Path
import config.item
# 프로젝트 루트를 sys.path에 추가
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))


def print_all_bot_info():
    """모든 BotInfo 정보 출력"""
    try:
        from data.persistence.sqlalchemy.core.session_factory import SessionFactory
        from data.persistence.sqlalchemy.repositories import SQLAlchemyBotInfoRepository

        session_factory = SessionFactory()
        session = session_factory.create_session()
        bot_repo = SQLAlchemyBotInfoRepository(session)
        bots = bot_repo.find_all()

        if bots:
            print(f"\n🤖 BotInfo ({len(bots)}개):")
            for bot in bots:
                active_emoji = "✅" if bot.active else "⏸️"
                print(
                    f"   {active_emoji} {bot.name} ({bot.symbol}): "
                    f"Seed={bot.seed:,.0f}$ | PR={bot.profit_rate*100:.0f}% | "
                    f"T_div={bot.t_div} | Max={bot.max_tier}T | "
                    f"AddedSeed={bot.added_seed:,.0f}$"
                )
        else:
            print("⚠️ BotInfo가 없습니다.")
        session.close()
    except Exception as e:
        print(f"❌ BotInfo 출력 실패: {str(e)}")


def print_all_trade():
    """모든 Trade 정보 출력"""
    try:
        from data.persistence.sqlalchemy.core.session_factory import SessionFactory
        from data.persistence.sqlalchemy.repositories import SQLAlchemyTradeRepository

        session_factory = SessionFactory()
        session = session_factory.create_session()
        trade_repo = SQLAlchemyTradeRepository(session)
        trades = trade_repo.find_all()

        if trades:
            print(f"\n📊 Trade ({len(trades)}개):")
            for trade in trades:
                print(
                    f"   - {trade.name} ({trade.symbol}): "
                    f"Price={trade.purchase_price:,.2f}$ | Amount={trade.amount:.2f} | "
                    f"Total={trade.total_price:,.2f}$ | Type={trade.trade_type.value} | "
                    f"Added={trade.date_added.strftime('%Y-%m-%d %H:%M')}"
                )
        else:
            print("⚠️ Trade 정보가 없습니다.")
        session.close()
    except Exception as e:
        print(f"❌ Trade 출력 실패: {str(e)}")


def print_all_order():
    """모든 Order 정보 출력"""
    try:
        from data.persistence.sqlalchemy.core.session_factory import SessionFactory
        from data.persistence.sqlalchemy.repositories import SQLAlchemyOrderRepository

        session_factory = SessionFactory()
        session = session_factory.create_session()
        order_repo = SQLAlchemyOrderRepository(session)
        orders = order_repo.find_all()

        if orders:
            print(f"\n📝 Order ({len(orders)}개):")
            for order in orders:
                print(
                    f"   - {order.name} ({order.symbol}): "
                    f"Type={order.order_type.value} | "
                    f"Progress={order.trade_count}/{order.total_count} | "
                    f"Remain={order.remain_value:,.2f}$ / Total={order.total_value:,.2f}$ | "
                    f"Added={order.date_added.strftime('%Y-%m-%d %H:%M')}"
                )
        else:
            print("⚠️ Order 정보가 없습니다.")
        session.close()
    except Exception as e:
        print(f"❌ Order 출력 실패: {str(e)}")


def print_all_history(limit: int = 20):
    """최근 History 정보 출력 (기본 20개)"""
    try:
        from data.persistence.sqlalchemy.core.session_factory import SessionFactory
        from data.persistence.sqlalchemy.repositories import SQLAlchemyHistoryRepository

        session_factory = SessionFactory()
        session = session_factory.create_session()
        history_repo = SQLAlchemyHistoryRepository(session)
        histories = history_repo.find_all()

        if histories:
            # 최신순으로 정렬 (trade_date 기준)
            histories_sorted = sorted(histories, key=lambda h: h.trade_date, reverse=True)[:limit]
            total_profit = sum(h.profit for h in histories)

            print(f"\n💰 History (최근 {len(histories_sorted)}개 / 전체 {len(histories)}개, 총 수익: {total_profit:,.2f}$):")
            for history in histories_sorted:
                profit_emoji = "🔺" if history.profit >= 0 else "🔻"
                print(
                    f"   {profit_emoji} {history.name} ({history.symbol}): "
                    f"Buy={history.buy_price:,.2f}$ → Sell={history.sell_price:,.2f}$ | "
                    f"Amount={history.amount:.0f} | "
                    f"Profit={history.profit:,.2f}$ ({history.profit_rate*100:.2f}%) | "
                    f"Type={history.trade_type.value} | "
                    f"Date={history.trade_date.strftime('%Y-%m-%d')}"
                )
        else:
            print("⚠️ History 정보가 없습니다.")
        session.close()
    except Exception as e:
        print(f"❌ History 출력 실패: {str(e)}")


def print_all_status():
    """Status 정보 출력"""
    try:
        from data.persistence.sqlalchemy.core.session_factory import SessionFactory
        from data.persistence.sqlalchemy.repositories import SQLAlchemyStatusRepository

        session_factory = SessionFactory()
        session = session_factory.create_session()
        status_repo = SQLAlchemyStatusRepository(session)
        status = status_repo.get_status()

        if status:
            print(f"\n💵 Status:")
            print(f"   - 입금: {status.deposit_won:,.0f}₩ / {status.deposit_dollar:,.2f}$")
            print(f"   - 출금: {status.withdraw_won:,.0f}₩ / {status.withdraw_dollar:,.2f}$")
            net_won = status.deposit_won - status.withdraw_won
            net_dollar = status.deposit_dollar - status.withdraw_dollar
            print(f"   - 순입금: {net_won:,.0f}₩ / {net_dollar:,.2f}$")
        else:
            print("⚠️ Status 정보가 없습니다.")
        session.close()
    except Exception as e:
        print(f"❌ Status 출력 실패: {str(e)}")


def print_all_db():
    """모든 DB 테이블 정보 출력"""
    print("=" * 80)
    print("📚 EggMoney Database Overview")
    print("=" * 80)
    print_all_bot_info()
    print_all_trade()
    print_all_order()
    print_all_history(limit=10)
    print_all_status()
    print("=" * 80)


if __name__ == "__main__":
    # print_db.py를 직접 실행할 때 DB 출력
    print_all_db()

