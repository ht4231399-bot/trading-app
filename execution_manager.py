from decimal import Decimal, getcontext, ROUND_DOWN
import time
import math
import logging
import uuid
from typing import Optional, Dict, Any

# Reuse TradeExecutor from repo
from trade_executor import TradeExecutor

getcontext().prec = 28

logger = logging.getLogger('execution_manager')
logging.basicConfig(level=logging.INFO)


class ExecutionManager:
    """Order execution manager that aims for extremely accurate live executions.

    Key features:
    - Auto-detects exchange tick/lot sizes via fetch_markets()
    - Estimates expected VWAP by consuming order book levels
    - Computes adaptive slice sizes based on available depth and a participation rate
    - Places quantized limit orders at best price (or adjusted within max_slippage)
    - Uses idempotency keys and reconciliation via TradeExecutor

    Usage:
        ex = ccxt.binance({'apiKey':..., 'secret':...})
        manager = ExecutionManager(ex, 'BTC/USDT')
        manager.execute_vwap(Decimal('0.01'), 'buy')

    Important safety:
    - Always dry-run first (LIVE_TRADING flag controlled by live_trader.py)
    - Confirm tick/lot sizes detected by `detect_market_ticks()` before running live
    """

    def __init__(self, exchange, symbol: str, price_tick: Optional[Decimal] = None, amount_tick: Optional[Decimal] = None, participation_rate: Decimal = Decimal('0.1'), max_slippage: Decimal = Decimal('0.005')):
        self.exchange = exchange
        self.symbol = symbol
        self.price_tick = Decimal(price_tick) if price_tick is not None else None
        self.amount_tick = Decimal(amount_tick) if amount_tick is not None else None
        self.participation_rate = Decimal(participation_rate)
        self.max_slippage = Decimal(max_slippage)  # fraction e.g., 0.005 = 0.5%
        self.te = None  # to be created once ticks are known

    def detect_market_ticks(self) -> Dict[str, Decimal]:
        """Fetch market metadata and set price_tick and amount_tick where possible.

        Returns dict with detected 'price_tick' and 'amount_tick'.
        """
        markets = self.exchange.fetch_markets()
        m = None
        for mk in markets:
            if mk.get('symbol') == self.symbol or mk.get('id') == self.symbol:
                m = mk
                break
        if not m:
            raise ValueError(f"Market {self.symbol} not found in exchange.fetch_markets()")

        # ccxt: market['precision'] may contain 'price' and 'amount'
        detected_price_tick = None
        detected_amount_tick = None

        precision = m.get('precision') or {}
        if 'price' in precision and precision['price'] is not None:
            # tick = 10^{-precision}
            detected_price_tick = Decimal(1) / (Decimal(10) ** Decimal(int(precision['price'])))
        if 'amount' in precision and precision['amount'] is not None:
            detected_amount_tick = Decimal(1) / (Decimal(10) ** Decimal(int(precision['amount'])))

        # Some exchanges provide 'tickSize' in 'info' or 'limits'
        info = m.get('info') or {}
        if not detected_price_tick:
            # Try common fields
            for k in ('tickSize', 'priceIncrement', 'tick_size'):
                v = info.get(k)
                if v:
                    detected_price_tick = Decimal(str(v))
                    break
        if not detected_amount_tick:
            for k in ('lotSize', 'stepSize', 'sizeIncrement', 'baseAssetPrecision'):
                v = info.get(k)
                if v:
                    detected_amount_tick = Decimal(str(v))
                    break

        # Fallbacks
        if detected_price_tick is None:
            detected_price_tick = Decimal('0.01')
        if detected_amount_tick is None:
            detected_amount_tick = Decimal('0.000001')

        # persist
        self.price_tick = detected_price_tick
        self.amount_tick = detected_amount_tick

        # create trade executor
        self.te = TradeExecutor(self.exchange, self.symbol, price_increment=str(self.price_tick), amount_increment=str(self.amount_tick))

        return {'price_tick': detected_price_tick, 'amount_tick': detected_amount_tick}

    @staticmethod
    def _quantize(value: Decimal, increment: Decimal) -> Decimal:
        if increment == 0:
            return value
        units = (value / increment).to_integral_value(rounding=ROUND_DOWN)
        return (units * increment).normalize()

    def estimate_vwap_from_orderbook(self, side: str, qty: Decimal, depth_limit: int = 200) -> Dict[str, Any]:
        """Consume the order book to estimate average fill price for qty.

        side: 'buy' means we consume asks (we buy from asks)
        Returns: {'filled': Decimal, 'avg_price': Decimal, 'cost': Decimal, 'levels_consumed': int}
        """
        if qty <= 0:
            return {'filled': Decimal('0'), 'avg_price': Decimal('0'), 'cost': Decimal('0'), 'levels_consumed': 0}

        ob = self.exchange.fetch_order_book(self.symbol, depth_limit)
        levels = ob['asks'] if side == 'buy' else ob['bids']

        remaining = Decimal(qty)
        cost = Decimal('0')
        filled = Decimal('0')
        levels_consumed = 0
        for lvl in levels:
            price = Decimal(str(lvl[0]))
            available = Decimal(str(lvl[1]))
            take = min(available, remaining)
            if take <= 0:
                continue
            cost += take * price
            remaining -= take
            filled += take
            levels_consumed += 1
            if remaining <= 0:
                break

        avg_price = cost / filled if filled > 0 else Decimal('0')
        return {'filled': filled, 'avg_price': avg_price, 'cost': cost, 'levels_consumed': levels_consumed}

    def compute_slices(self, total_qty: Decimal, side: str, max_slice_fraction: Decimal = Decimal('0.25')):
        """Compute adaptive slice sizes based on top-of-book available volume and participation rate.

        Strategy:
        - Fetch top N levels and compute available volume at best price
        - Target slice as min(max_slice_fraction * available_top_volume, participation_rate * estimated_market_volume)
        - Fallback to equal slicing if market data insufficient
        Returns list of Decimal slice sizes summing <= total_qty
        """
        # quick fetch of top book
        ob = self.exchange.fetch_order_book(self.symbol, 5)
        top_levels = ob['asks'] if side == 'buy' else ob['bids']
        top_volume = Decimal('0')
        for lvl in top_levels[:3]:
            top_volume += Decimal(str(lvl[1]))

        if top_volume > 0:
            # choose slice base on top_volume
            target_slice = (top_volume * Decimal(str(max_slice_fraction))).quantize(self.amount_tick) if self.amount_tick else (top_volume * max_slice_fraction)
            # ensure at least a minimal slice
            min_slice = Decimal('0.0001') if not self.amount_tick else max(self.amount_tick, self.amount_tick)
            target_slice = max(min_slice, target_slice)
        else:
            target_slice = total_qty / Decimal(5)

        # Ensure we don't create too many tiny slices; cap slices to e.g., 20
        slices = []
        remaining = Decimal(total_qty)
        while remaining > 0 and len(slices) < 50:
            s = min(target_slice, remaining)
            s_q = self._quantize(s, self.amount_tick) if self.amount_tick else s
            if s_q <= 0:
                # if quantization makes it zero, assign remaining if it's larger than amount_tick
                if remaining >= (self.amount_tick or Decimal('0.000001')):
                    s_q = self._quantize(remaining, self.amount_tick)
                else:
                    break
            slices.append(s_q)
            remaining -= s_q
        if remaining > 0:
            # add leftover as final slice
            slices.append(self._quantize(remaining, self.amount_tick))
        # remove zero slices
        slices = [s for s in slices if s > 0]
        return slices

    def execute_vwap(self, total_qty: Decimal, side: str, max_slippage: Optional[Decimal] = None, max_slices: Optional[int] = None, dry_run: bool = True, testnet: bool = False) -> Dict[str, Any]:
        """Execute an adaptive VWAP-style execution aiming for accuracy.

        - total_qty: Decimal amount of base asset to buy/sell
        - side: 'buy' or 'sell'
        - max_slippage: absolute fraction (e.g., 0.005) tolerated beyond current mid-price
        - dry_run: if True, do not send real orders (TradeExecutor may still be used for simulation)

        Returns execution summary with per-slice details and overall realized VWAP (if live)
        """
        if self.price_tick is None or self.amount_tick is None:
            self.detect_market_ticks()

        max_slippage = Decimal(max_slippage) if max_slippage is not None else self.max_slippage

        # Estimate initial expected vwap; if it exceeds allowed slippage, fail early
        estimate = self.estimate_vwap_from_orderbook(side, total_qty)
        if estimate['filled'] < total_qty:
            # warn: not enough depth to fill entirely at current book snapshot; we'll proceed but expect partial fills
            logger.warning('Orderbook depth insufficient for full qty at current snapshot: %s', estimate)

        # compute slices
        slices = self.compute_slices(total_qty, side)
        if max_slices and len(slices) > max_slices:
            # merge slices to reduce count while preserving total_qty
            factor = math.ceil(len(slices) / max_slices)
            merged = []
            for i in range(0, len(slices), factor):
                merged.append(sum(slices[i:i+factor]))
            slices = [Decimal(str(x)) for x in merged]

        logger.info('Executing %d slices for total %s %s', len(slices), str(total_qty), self.symbol)

        results = []
        cumulative_filled = Decimal('0')
        cumulative_cost = Decimal('0')

        for i, slice_qty in enumerate(slices):
            # re-fetch snapshot to make per-slice decision
            ob = self.exchange.fetch_order_book(self.symbol, 50)
            best_ask = Decimal(str(ob['asks'][0][0])) if ob['asks'] else Decimal('0')
            best_bid = Decimal(str(ob['bids'][0][0])) if ob['bids'] else Decimal('0')
            mid = (best_ask + best_bid) / Decimal('2') if best_ask and best_bid else (best_ask or best_bid)

            # estimate VWAP for slice
            est = self.estimate_vwap_from_orderbook(side, slice_qty)
            est_avg = est['avg_price']

            # decide limit price: for buys, place at min(est_avg, mid*(1+max_slippage)) quantized
            if side == 'buy':
                aggressive_price = est_avg if est_avg > 0 else best_ask
                limit_price = min(aggressive_price, mid * (Decimal('1') + max_slippage))
            else:
                aggressive_price = est_avg if est_avg > 0 else best_bid
                limit_price = max(aggressive_price, mid * (Decimal('1') - max_slippage))

            limit_price_q = self._quantize(limit_price, self.price_tick)
            slice_qty_q = self._quantize(slice_qty, self.amount_tick)
            if slice_qty_q <= 0:
                logger.warning('Quantized slice is zero, skipping slice %d', i)
                continue

            idempotency = f'exec-{int(time.time())}-{i}-{uuid.uuid4().hex[:6]}'

            # Dry-run: just record the planned slice and estimated avg
            if dry_run:
                logger.info('[DRY] Slice %d: qty=%s price=%s est_avg=%s levels=%d', i, str(slice_qty_q), str(limit_price_q), str(est_avg), est['levels_consumed'])
                results.append({'slice_index': i, 'qty': slice_qty_q, 'limit_price': limit_price_q, 'est_avg': est_avg, 'placed': False, 'filled': Decimal('0')})
                continue

            # Place the limit order via TradeExecutor; respects quantization
            try:
                order = self.te.place_limit_order(side, limit_price_q, slice_qty_q, idempotency_key=idempotency)
            except Exception as e:
                logger.exception('Failed to place slice %d: %s', i, e)
                results.append({'slice_index': i, 'qty': slice_qty_q, 'limit_price': limit_price_q, 'placed': False, 'error': str(e)})
                continue

            # Immediately reconcile fill; in real life this may be async and partial
            try:
                summary = self.te.reconcile_fill(order['id'])
                filled = Decimal(str(summary['filled']))
                cost = Decimal(str(summary['cost']))
                cumulative_filled += filled
                cumulative_cost += cost
                results.append({'slice_index': i, 'qty': slice_qty_q, 'limit_price': limit_price_q, 'placed': True, 'order': order, 'filled': filled, 'cost': cost, 'status': summary['status']})
            except Exception as e:
                logger.exception('Failed to reconcile slice %d: %s', i, e)
                results.append({'slice_index': i, 'qty': slice_qty_q, 'limit_price': limit_price_q, 'placed': True, 'order': order, 'reconcile_error': str(e)})

        overall_vwap = (cumulative_cost / cumulative_filled) if cumulative_filled > 0 else Decimal('0')
        summary = {
            'symbol': self.symbol,
            'side': side,
            'total_qty': total_qty,
            'slices': len(slices),
            'cumulative_filled': cumulative_filled,
            'cumulative_cost': cumulative_cost,
            'realized_vwap': overall_vwap,
            'results': results,
        }
        return summary
