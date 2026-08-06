# Live trading: how to enable and safety checklist

This repository includes a safe, opt-in helper (live_trader.py) to place real orders through exchanges supported by ccxt. Live mode is disabled by default — this is deliberate.

Quickstart (dry-run first)
1. Create a Python virtual environment and install deps:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install ccxt python-dotenv

2. Copy .env.example -> .env and fill in your exchange API keys (DO NOT commit .env)

3. Run a dry-run: by default LIVE_TRADING is false so the script will only log the intended order.
   python live_trader.py --exchange binance --symbol BTC/USDT --side buy --amount 0.001 --price 30000 --type limit

4. To enable live trading, set LIVE_TRADING=true in your environment or .env. I strongly recommend using exchange sandbox/testnet first:
   python live_trader.py --exchange binance --symbol BTC/USDT --side buy --amount 0.001 --price 30000 --type limit --testnet

Safety checklist before enabling LIVE_TRADING=true
- Verify tick and lot sizes for the symbol via exchange.fetch_markets() and pass correct --price_tick and --amount_tick values.
- Set small amounts and test on sandbox/testnet first.
- Ensure your API key has only the permissions you intend (trading only, no withdrawals if possible).
- Keep a secure backup of keys and rotate them after testing.
- Review logs in ORDER_LOG_PATH and implement a DB-backed audit in production.

If you want, I can:
- Wire this backend to your frontend so a selected UI action will trigger a dry-run or live order (with confirmations).
- Add exchange.fetch_markets() logic to auto-detect tick/lot sizes and persist them per symbol.
- Add market order simulation and limit order post-only handling.
