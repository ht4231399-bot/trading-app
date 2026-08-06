import pytest
from decimal import Decimal
from trade_executor import TradeExecutor


class DummyExchange:
    def __init__(self):
        self.orders = {}
        self.counter = 0

    def create_order(self, symbol, type_, side, amount, price, params):
        self.counter += 1
        oid = f"order-{self.counter}"
        # store the exact values the executor sent so tests can validate quantization
        self.orders[oid] = {
            'id': oid,
            'symbol': symbol,
            'side': side,
            'amount': str(amount),
            'price': str(price),
            'filled': '0',
            'status': 'open',
            'params': params,
        }
        return self.orders[oid]

    def fetch_order(self, oid, symbol):
        return self.orders[oid]


def test_place_limit_order_quantizes():
    ex = DummyExchange()
    te = TradeExecutor(ex, 'BTC/USD', price_increment='0.01', amount_increment='0.001')
    # price 123.456 should quantize to 123.45, amount 0.0047 -> 0.004
    order = te.place_limit_order('buy', Decimal('123.456'), Decimal('0.0047'), idempotency_key='k1')
    assert order['price'] == str(float(Decimal('123.45')))
    assert order['amount'] == str(float(Decimal('0.004')))
    assert order['params']['idempotency_key'] == 'k1'


def test_place_twap_splits_and_quantizes():
    ex = DummyExchange()
    te = TradeExecutor(ex, 'ETH/USD', price_increment='0.1', amount_increment='0.01')
    orders = te.place_twap('sell', Decimal('0.05'), Decimal('200.0'), slices=3, delay_seconds=0.0)
    # total requested 0.05 with amount_increment 0.01 -> quantized slices: 0.016 -> 0.01 for first two, last will be quantized remaining
    assert len(orders) >= 1
    sum_amounts = sum(Decimal(o['amount']) for o in orders)
    # Because of quantization down, total filled/requested should be <= original total_amount
    assert sum_amounts <= Decimal('0.05')
