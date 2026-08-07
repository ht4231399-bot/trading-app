#!/usr/bin/env python3
"""
live_rates.py

Improved live rates broadcaster:
- Attempts to match provided symbols to exchange market symbols using a normalization heuristic.
- Quantizes bid/ask using detected market tick/precision before broadcasting so frontends do not re-quantize.
- Sends `bid`, `ask`, `mid`, `tick`, `decimals`, and `market_symbol` fields as strings for exactness.
- Skips symbols that cannot be resolved on the exchange and logs them.
"""

import os
import asyncio
import json
import logging
from decimal import Decimal
from typing import List, Dict, Optional

import ccxt
import websockets
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('live_rates')

EXCHANGE = os.getenv('EXCHANGE', 'binance')
SYMBOLS = os.getenv('SYMBOLS', 'EUR/USD,GBP/USD,USD/JPY,AUD/USD,USD/CHF,NZD/USD,BTC/USDT,ETH/USDT,BNB/USDT,ADA/USDT,SOL/USDT')
POLL_INTERVAL = float(os.getenv('POLL_INTERVAL', '1.0'))
WS_HOST = os.getenv('WS_HOST', '0.0.0.0')
WS_PORT = int(os.getenv('WS_PORT', '8765'))

# Parse symbols into list
SYMBOL_LIST = [s.strip() for s in SYMBOLS.split(',') if s.strip()]

# Maintain set of connected websockets
CLIENTS = set()


def normalize_symbol_for_match(s: str) -> str:
    """Return normalized alphanumeric uppercase form for loose matching between symbol names."""
    return ''.join(ch for ch in s if ch.isalnum()).upper()


async def broadcaster():
    ex_class = getattr(ccxt, EXCHANGE)
    exchange = ex_class({'enableRateLimit': True})

    # pre-fetch markets to get precision/tick info
    try:
        markets = exchange.fetch_markets()
    except Exception as e:
        logger.warning('Failed to fetch markets metadata: %s', e)
        markets = []

    # Build convenience maps
    market_by_symbol = {m['symbol']: m for m in markets}
    market_by_norm = {normalize_symbol_for_match(m['symbol']): m for m in markets}

    # Resolve requested symbols to exchange market symbols where possible
    resolved: Dict[str, Dict] = {}
    for user_sym in SYMBOL_LIST:
        # Try direct match
        if user_sym in market_by_symbol:
            resolved[user_sym] = market_by_symbol[user_sym]
            continue
        # Try normalized match
        norm = normalize_symbol_for_match(user_sym)
        if norm in market_by_norm:
            resolved[user_sym] = market_by_norm[norm]
            continue
        # Not found yet; we'll still attempt to fetch ticker directly later, but mark as unresolved
        resolved[user_sym] = None

    logger.info('Resolved %d/%d symbols to exchange markets', sum(1 for v in resolved.values() if v), len(resolved))

    while True:
        updates = []
        for user_sym in SYMBOL_LIST:
            try:
                market = resolved.get(user_sym)
                market_symbol = market['symbol'] if market else user_sym

                # Attempt to fetch ticker; if market_symbol doesn't exist, ccxt may still accept user_sym in some cases
                try:
                    ticker = exchange.fetch_ticker(market_symbol)
                except Exception:
                    # Try the original user_sym as fallback
                    ticker = exchange.fetch_ticker(user_sym)
                    market_symbol = ticker.get('symbol', user_sym)

                bid = ticker.get('bid')
                ask = ticker.get('ask')
                if bid is None or ask is None:
                    # skip if no data
                    logger.debug('Ticker missing bid/ask for %s; skipping', user_sym)
                    continue

                bid_d = Decimal(str(bid))
                ask_d = Decimal(str(ask))

                # determine tick/decimals from market if available
                tick = Decimal('0.01')
                decimals = 2
                mk = market or market_by_symbol.get(market_symbol)
                if mk:
                    precision = mk.get('precision') or {}
                    if precision.get('price') is not None:
                        p = int(precision.get('price'))
                        tick = Decimal(1) / (Decimal(10) ** p)
                        decimals = p
                    else:
                        info = mk.get('info') or {}
                        for k in ('tickSize', 'priceIncrement', 'tick_size'):
                            if info.get(k):
                                tick = Decimal(str(info.get(k)))
                                decimals = max(0, -tick.as_tuple().exponent)
                                break

                # Quantize bid/ask DOWN to tick to ensure accuracy and avoid frontend re-quantization issues
                def quantize_down(value: Decimal, step: Decimal) -> Decimal:
                    if step == 0:
                        return value
                    units = (value / step).to_integral_value(rounding='ROUND_FLOOR')
                    return (units * step).normalize()

                # Use Decimal quantization and format as strings to preserve exactness over JSON
                bid_q = (bid_d // tick) * tick if tick != 0 else bid_d
                ask_q = (ask_d // tick) * tick if tick != 0 else ask_d
                mid_q = ((bid_q + ask_q) / Decimal(2)).quantize(tick) if tick != 0 else (bid_q + ask_q) / Decimal(2)

                update = {
                    'symbol': user_sym,
                    'market_symbol': market_symbol,
                    'bid': format(bid_q, 'f'),
                    'ask': format(ask_q, 'f'),
                    'mid': format(mid_q, 'f'),
                    'tick': format(tick, 'f'),
                    'decimals': int(decimals),
                    'ts': int(asyncio.get_event_loop().time() * 1000),
                }
                updates.append(update)
            except Exception as e:
                logger.debug('Skipping symbol %s due to error: %s', user_sym, e)

        if updates:
            message = json.dumps({'type': 'tickers', 'data': updates})
            coros = []
            for ws in list(CLIENTS):
                coros.append(send_safe(ws, message))
            if coros:
                await asyncio.gather(*coros, return_exceptions=True)
        await asyncio.sleep(POLL_INTERVAL)


async def send_safe(ws, message: str):
    try:
        await ws.send(message)
    except Exception as e:
        logger.debug('Send failed, removing client: %s', e)
        try:
            CLIENTS.discard(ws)
            await ws.close()
        except Exception:
            pass


async def handler(websocket, path):
    logger.info('Client connected: %s', websocket.remote_address)
    CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CLIENTS.discard(websocket)
        logger.info('Client disconnected: %s', websocket.remote_address)


def main():
    logger.info('Starting live rates server for exchange=%s symbols=%s host=%s port=%s poll=%ss', EXCHANGE, ','.join(SYMBOL_LIST), WS_HOST, WS_PORT, POLL_INTERVAL)
    loop = asyncio.get_event_loop()
    start_server = websockets.serve(handler, WS_HOST, WS_PORT)
    loop.run_until_complete(start_server)
    try:
        loop.run_until_complete(broadcaster())
    except KeyboardInterrupt:
        logger.info('Shutting down live rates server')


if __name__ == '__main__':
    main()
