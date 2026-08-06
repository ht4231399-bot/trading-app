from decimal import Decimal, getcontext, ROUND_DOWN
import time
from typing import Optional

# Set high precision for monetary calculations
getcontext().prec = 28


class TradeExecutor:
    """A Decimal-based trade executor that enforces symbol increments, idempotency, TWAP slicing,
    and reconciliation helpers to make trades accurate and auditable.

    Notes:
    - Uses Decimal for all internal arithmetic; avoid floats for money.
    - Exchange adapters should implement `create_order(symbol, type, side, amount, price, params)`
      and `fetch_order(order_id, symbol)` similar to ccxt. When integrating with a particular
      exchange SDK, adapt the parameter names and idempotency support accordingly.
    """

    def __init__(self, exchange, symbol: str, price_increment: str, amount_increment: str):
        """
        exchange: an exchange client implementing create_order and fetch_order
        symbol: market symbol (e.g., 'BTC/USDT')
        price_increment: smallest price tick e.g. '0.01'
        amount_increment: smallest lot size e.g. '0.000001'
        """
        self.exchange = exchange
        self.symbol = symbol
        self.price_increment = Decimal(str(price_increment))
        self.amount_increment = Decimal(str(amount_increment))

    def _quantize(self, value: Decimal, increment: Decimal) -> Decimal:
        """Round down `value` to the nearest multiple of `increment` to avoid invalid orders.

        Uses FLOOR rounding to ensure we never request an amount/price that the exchange would
        reject for exceeding precision or minimum increment.
        """
        if increment == 0:
            return value
        # number of increments
        units = (value / increment).to_integral_value(rounding=ROUND_DOWN)
        return (units * increment).normalize()

    def place_limit_order(self, side: str, price: Decimal, amount: Decimal, idempotency_key: Optional[str] = None):
        """Place a quantized limit order.

        Returns the raw order object from the exchange adapter.
        """
        price = Decimal(price)
        amount = Decimal(amount)
        price_q = self._quantize(price, self.price_increment)
        amount_q = self._quantize(amount, self.amount_increment)
        if amount_q <= 0:
            raise ValueError("quantized amount is zero or negative; increase total amount or reduce increment")

        params = {}
        if idempotency_key:
            # Many exchanges support idempotency via headers or params; adapt when integrating.
            params["idempotency_key"] = idempotency_key

        # Exchange SDKs often expect floats; convert intentionally but store/record Decimals in your DB.
        order = self.exchange.create_order(self.symbol, 'limit', side, float(amount_q), float(price_q), params)
        return order

    def place_twap(self, side: str, total_amount: Decimal, target_price: Decimal, slices: int = 5, delay_seconds: float = 1.0):
        """Simple TWAP: split total_amount into `slices` quantized pieces and place sequential limit orders.

        Returns list of exchange order responses.
        """
        total_amount = Decimal(total_amount)
        target_price = Decimal(target_price)
        if slices < 1:
            raise ValueError("slices must be >= 1")

        per_slice = total_amount / Decimal(slices)
        per_slice_q = self._quantize(per_slice, self.amount_increment)

        orders = []
        remaining = total_amount
        timestamp = int(time.time() * 1000)
        for i in range(slices):
            if i < slices - 1:
                amt = per_slice_q
            else:
                # last slice gets remaining, quantized down
                amt = self._quantize(remaining, self.amount_increment)
            if amt <= 0:
                break
            remaining -= amt
            key = f"twap-{timestamp}-{i}"
            order = self.place_limit_order(side, target_price, amt, idempotency_key=key)
            orders.append(order)
            if delay_seconds > 0 and i < slices - 1:
                time.sleep(delay_seconds)
        return orders

    def reconcile_fill(self, order_id: str):
        """Fetch order and return Decimal-typed fill information for reconciliation.

        Returns: { 'filled': Decimal, 'cost': Decimal, 'fee': Decimal, 'status': str }
        """
        raw = self.exchange.fetch_order(order_id, self.symbol)
        # Exchanges may return different shapes; normalize carefully when integrating.
        filled = Decimal(str(raw.get('filled') or raw.get('amount_filled') or 0))
        cost = Decimal(str(raw.get('cost') or raw.get('filled_cost') or 0))
        fee = Decimal(str((raw.get('fee') or {}).get('cost') or raw.get('fee_cost') or 0))
        status = raw.get('status')
        return {'filled': filled, 'cost': cost, 'fee': fee, 'status': status}
