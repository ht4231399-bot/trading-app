import pytest
from decimal import Decimal
from execution_manager import ExecutionManager

class DummyBookExchange:
    def __init__(self, book):
        self._book = book
    def fetch_markets(self):
        return [{'symbol':'BTC/USDT','precision':{'price':2,'amount':6},'info':{}}]
    def fetch_order_book(self, symbol, limit=50):
        return self._book
    def fetch_markets(self):
        return [{'symbol':'BTC/USDT','precision':{'price':2,'amount':6},'info':{}}]


def test_estimate_vwap_simple():
    # create a simple book: asks and bids
    book = {
        'bids': [[30000, 0.5], [29950, 1.0]],
        'asks': [[30010, 0.3], [30020, 1.0]]
    }
    ex = DummyBookExchange(book)
    em = ExecutionManager(ex, 'BTC/USDT')
    em.detect_market_ticks()
    res = em.estimate_vwap_from_orderbook('buy', Decimal('0.3'))
    assert res['filled'] == Decimal('0.3')
    assert res['levels_consumed'] >= 1


def test_compute_slices_basic():
    book = {'bids': [[1,1]], 'asks': [[1,1]]}
    ex = DummyBookExchange(book)
    em = ExecutionManager(ex, 'BTC/USDT')
    em.detect_market_ticks()
    slices = em.compute_slices(Decimal('0.05'), 'buy')
    assert sum(slices) <= Decimal('0.05')
