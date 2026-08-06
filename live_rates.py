#!/usr/bin/env python3
"""
live_rates.py

Fetch live tickers from a public exchange (ccxt) and broadcast over a WebSocket to frontends.

Usage:
  - pip install -r requirements.txt
  - pip install websockets python-dotenv
  - Edit .env or pass env vars:
      EXCHANGE=binance
      SYMBOLS=BTC/USDT,ETH/USDT,EUR/USD
      POLL_INTERVAL=1.0
      WS_HOST=0.0.0.0
      WS_PORT=8765
  - Run: python live_rates.py

The server will broadcast JSON arrays of updates each poll. Each update item:
  {"symbol":"BTC/USDT","bid":"67500.12","ask":"67520.00","tick":"0.01","decimals":2,"ts":162...}

The frontend (app.js) connects to ws://host:port and applies the updates to the displayed rates.
"""

import os
import asyncio
import json
import logging
from decimal import Decimal
from typing import List, Dict

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


async def broadcaster():
    """Main loop: fetch tickers and broadcast to clients every POLL_INTERVAL seconds."""
    # instantiate ccxt exchange (public access for ticker data)
    ex_class = getattr(ccxt, EXCHANGE)
    exchange = ex_class({'enableRateLimit': True})

    # pre-fetch markets to get precision/tick info
    try:
        markets = exchange.fetch_markets()
        market_map = {m['symbol']: m for m in markets}
    except Exception as e:
        logger.warning('Failed to fetch markets metadata: %s', e)
        market_map = {}

    while True:
        updates = []
        for symbol in SYMBOL_LIST:
            try:
                # Some exchange symbol naming differs (e.g., BTC/USDT vs BTC/USDT) - assume provided format matches exchange
                ticker = exchange.fetch_ticker(symbol)
                bid = ticker.get('bid') or ticker.get('last')
                ask = ticker.get('ask') or ticker.get('last')
                if bid is None or ask is None:
                    # skip if no data
                    continue

                bid_d = Decimal(str(bid))
                ask_d = Decimal(str(ask))

                # detect tick/decimals
                tick = Decimal('0.01')
                decimals = 2
                mk = market_map.get(symbol)
                if mk:
                    precision = mk.get('precision') or {}
                    if precision.get('price') is not None:
                        p = int(precision.get('price'))
                        tick = Decimal(1) / (Decimal(10) ** p)
                        decimals = p
                    else:
                        info = mk.get('info') or {}
                        # try common fields
                        for k in ('tickSize', 'priceIncrement', 'tick_size'):
                            if info.get(k):
                                tick = Decimal(str(info.get(k)))
                                decimals = max(0, -tick.as_tuple().exponent)
                                break

                update = {
                    'symbol': symbol,
                    'bid': format(bid_d, 'f'),
                    'ask': format(ask_d, 'f'),
                    'tick': format(tick, 'f'),
                    'decimals': int(decimals),
                    'ts': int(asyncio.get_event_loop().time() * 1000),
                }
                updates.append(update)
            except Exception as e:
                logger.debug('Skipping symbol %s due to error: %s', symbol, e)

        if updates:
            message = json.dumps({'type': 'tickers', 'data': updates})
            # broadcast
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
        # keep connection open; no need to receive messages
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
