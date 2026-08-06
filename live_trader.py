"""
live_trader.py

Safe, opt-in live trading wrapper using ccxt + the Decimal-based TradeExecutor.

Design principles:
- Default to dry-run/simulated mode. Live mode only enabled when environment variable LIVE_TRADING=true.
- API keys MUST be provided via environment variables; never check them into the repo.
- Enforce per-symbol tick/lot quantization and min/max order amount checks before sending.
- Use idempotency keys and persistent order logging (simple file-based log for demo). In production, replace with DB.
- Rate-limit and retry basic policy.

Usage:
- pip install -r requirements.txt (ccxt, python-dotenv)
- Copy .env.example to .env and fill API keys
- Run: python live_trader.py --exchange binance --symbol BTC/USDT --side buy --amount 0.001 --price 30000 --type limit
- By default the script will print what it WOULD do. Set LIVE_TRADING=true in env to actually send orders.
"""

import os
import time
import uuid
import json
import logging
from decimal import Decimal
from typing import Optional

import ccxt
from dotenv import load_dotenv

# local import from repo
from trade_executor import TradeExecutor

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('live_trader')

# Safety switches via environment
LIVE_TRADING = os.getenv('LIVE_TRADING', 'false').lower() in ('1', 'true', 'yes')
ORDER_LOG_PATH = os.getenv('ORDER_LOG_PATH', 'live_orders.log')

# Basic retry policy
MAX_RETRIES = 3
RETRY_DELAY = 1.0


def get_ccxt_exchange(name: str, api_key: Optional[str], secret: Optional[str], enable_rate_limit: bool = True, testnet: bool = False):
    """Return configured ccxt exchange instance. Do NOT pass secrets directly in code; use env vars."""
    name = name.lower()
    if not hasattr(ccxt, name):
        raise ValueError(f"Unsupported exchange: {name}")
    ex_class = getattr(ccxt, name)
    config = {
        'enableRateLimit': enable_rate_limit,
    }
    # Many exchanges have sandbox/testnet endpoints; ccxt uses `test` or exchange.options['test'] depending on implementation.
    exchange = ex_class(config)

    if api_key and secret:
        exchange.apiKey = api_key
        exchange.secret = secret

    # Example: for some exchanges (binance) enable testnet via urls or options
    if testnet:
        if name == 'binance':
            exchange.set_sandbox_mode(True)
        elif name == 'bybit':
            exchange.urls['api'] = exchange.urls.get('test') or exchange.urls.get('api')
        # Add other exchange-specific testnet handling as required

    return exchange


def safe_create_trade_executor(exchange, symbol: str, price_increment: str, amount_increment: str) -> TradeExecutor:
    """Create the Decimal-based TradeExecutor for the exchange/symbol.

    In production you should fetch tick/lot sizes via exchange.fetch_markets() and use the real increments.
    """
    return TradeExecutor(exchange, symbol, price_increment=price_increment, amount_increment=amount_increment)


def log_order_attempt(entry: dict):
    entry['timestamp'] = int(time.time())
    with open(ORDER_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def place_limit_order(exchange_name: str, symbol: str, side: str, price: Decimal, amount: Decimal, price_tick: str, amount_tick: str, idempotency_key: Optional[str] = None, testnet: bool = False):
    """Place a limit order via TradeExecutor, with dry-run unless LIVE_TRADING.

    Returns the exchange response (or simulated response in dry-run).
    """
    api_key = os.getenv(f'{exchange_name.upper()}_API_KEY')
    api_secret = os.getenv(f'{exchange_name.upper()}_API_SECRET')

    exchange = get_ccxt_exchange(exchange_name, api_key, api_secret, enable_rate_limit=True, testnet=testnet)
    te = safe_create_trade_executor(exchange, symbol, price_increment=price_tick, amount_increment=amount_tick)

    # Safety pre-checks
    if amount <= 0:
        raise ValueError('Amount must be positive')
    if price <= 0:
        raise ValueError('Price must be positive')

    # Default idempotency key
    if not idempotency_key:
        idempotency_key = f"live-{int(time.time())}-{uuid.uuid4().hex[:8]}"

    attempt = {
        'exchange': exchange_name,
        'symbol': symbol,
        'side': side,
        'price': str(price),
        'amount': str(amount),
        'idempotency_key': idempotency_key,
        'live': LIVE_TRADING,
    }
    log_order_attempt({**attempt, 'phase': 'pre_send'})

    if not LIVE_TRADING:
        logger.info('[DRY RUN] Would place order: %s', attempt)
        return {'status': 'dry_run', 'details': attempt}

    last_err = None
    for r in range(MAX_RETRIES):
        try:
            # Place order via TradeExecutor
            order = te.place_limit_order(side, price, amount, idempotency_key=idempotency_key)
            logger.info('Order placed: %s', order)
            log_order_attempt({**attempt, 'phase': 'placed', 'order': order})
            return order
        except Exception as e:
            last_err = e
            logger.exception('Order placement failed, retrying... (%d/%d)', r+1, MAX_RETRIES)
            time.sleep(RETRY_DELAY * (r+1))
    # All retries failed
    log_order_attempt({**attempt, 'phase': 'failed', 'error': str(last_err)})
    raise last_err


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Safe Live Trader (dry-run by default).')
    parser.add_argument('--exchange', required=True, help='exchange id (ccxt name) e.g. binance')
    parser.add_argument('--symbol', required=True, help='market symbol e.g. BTC/USDT')
    parser.add_argument('--side', required=True, choices=['buy', 'sell'])
    parser.add_argument('--price', required=False, help='price for limit orders')
    parser.add_argument('--amount', required=True, help='order amount (base asset)')
    parser.add_argument('--type', choices=['limit', 'market'], default='limit')
    parser.add_argument('--price_tick', default=os.getenv('PRICE_TICK', '0.01'), help='price tick increment to quantize')
    parser.add_argument('--amount_tick', default=os.getenv('AMOUNT_TICK', '0.000001'), help='amount increment to quantize')
    parser.add_argument('--testnet', action='store_true', help='use exchange testnet/sandbox where available')

    args = parser.parse_args()

    price = Decimal(args.price) if args.price else None
    amount = Decimal(args.amount)

    if args.type == 'limit' and not price:
        parser.error('Limit orders require --price')

    if args.type == 'limit':
        resp = place_limit_order(args.exchange, args.symbol, args.side, price, amount, args.price_tick, args.amount_tick, testnet=args.testnet)
        print('Response:', resp)
    else:
        logger.error('Market order support not implemented in this simple script; use limit orders or extend safely.')

