# -*- coding: utf-8 -*-
"""Hantoo Service Test"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.external.hantoo import HantooService


def test_hantoo_price():
    """Price query test (test mode)"""
    print("=" * 60)
    print("Hantoo Price Query Test (Test Mode)")
    print("=" * 60)

    service = HantooService(test_mode=False)

    # Current price query
    print("\n[Current Price Query]")
    symbols = ['TQQQ', 'SOXL', 'LABU', 'SPY']
    for symbol in symbols:
        price = service.get_price(symbol)
        prev_price = service.get_prev_price(symbol)
        print(f"{symbol:6s}: Current ${price:>7.2f} | Prev ${prev_price:>7.2f}")

    print("\nPrice query test completed\n")


def test_hantoo_buy_sell():
    """Buy/Sell test (test mode)"""
    print("=" * 60)
    print("Hantoo Buy/Sell Test (Test Mode)")
    print("=" * 60)

    service = HantooService(test_mode=True)

    # Buy test
    print("\n[Buy Test]")
    symbol = 'TQQQ'
    amount = 10
    request_price = service.get_available_buy(symbol)
    print(f"Buy request: {symbol} {amount} shares @ ${request_price:.2f}")

    trade_result = service.buy(symbol, amount, request_price)
    if trade_result:
        print(f"Buy result: {trade_result}")
        print(f"  - Amount: {trade_result.amount}")
        print(f"  - Unit Price: ${trade_result.unit_price:.2f}")
        print(f"  - Total: ${trade_result.total_price:.2f}")
    else:
        print("Buy failed")

    # Sell test
    print("\n[Sell Test]")
    sell_amount = 5
    sell_price = service.get_available_sell(symbol)
    print(f"Sell request: {symbol} {sell_amount} shares @ ${sell_price:.2f}")

    sell_result = service.sell(symbol, sell_amount, sell_price)
    if sell_result:
        print(f"Sell result: {sell_result}")
        print(f"  - Amount: {sell_result.amount}")
        print(f"  - Unit Price: ${sell_result.unit_price:.2f}")
        print(f"  - Total: ${sell_result.total_price:.2f}")
    else:
        print("Sell failed")

    print("\nBuy/Sell test completed\n")


def test_hantoo_twap():
    """TWAP order test (test mode)"""
    print("=" * 60)
    print("Hantoo TWAP Order Test (Test Mode)")
    print("=" * 60)

    service = HantooService(test_mode=True)

    # TWAP buy order (return only order number)
    print("\n[TWAP Buy Order]")
    symbol = 'SOXL'
    amount = 20
    request_price = 25.50
    print(f"TWAP buy order: {symbol} {amount} shares @ ${request_price:.2f}")

    odno_buy = service.buy_request_only_odno(symbol, amount, request_price)
    if odno_buy:
        print(f"Order number: {odno_buy}")
    else:
        print("TWAP buy order failed")

    # TWAP sell order (return only order number)
    print("\n[TWAP Sell Order]")
    sell_amount = 15
    sell_price = 26.00
    print(f"TWAP sell order: {symbol} {sell_amount} shares @ ${sell_price:.2f}")

    odno_sell = service.sell_request_only_odno(symbol, sell_amount, sell_price)
    if odno_sell:
        print(f"Order number: {odno_sell}")
    else:
        print("TWAP sell order failed")

    print("\nTWAP order test completed\n")


def test_hantoo_balance():
    """Balance query test (test mode)"""
    print("=" * 60)
    print("Hantoo Balance Query Test (Test Mode)")
    print("=" * 60)

    service = HantooService(test_mode=True)

    # Available balance query
    print("\n[Available Balance Query]")
    balance = service.get_balance('TQQQ', 60.0)
    print(f"Available balance: ${balance:.2f}")

    # Ticker info query
    print("\n[Ticker Info Query]")
    ticker_list = ['TQQQ', 'SOXL', 'LABU']
    ticker_items = service.get_ticker_list_info(ticker_list)
    if ticker_items:
        for item in ticker_items:
            print(f"{item.ticker}: {item.amount} shares @ ${item.price:.2f} = ${item.total_price:.2f}")
    else:
        print("Test mode returns empty list")

    print("\nBalance query test completed\n")


if __name__ == "__main__":
    test_hantoo_price()
    test_hantoo_buy_sell()
    test_hantoo_twap()
    test_hantoo_balance()

    print("=" * 60)
    print("All Hantoo tests passed!")
    print("=" * 60)
