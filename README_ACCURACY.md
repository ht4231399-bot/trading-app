# Trading-app: Accurate Trading Enhancements

This commit adds a Decimal-based TradeExecutor module and tests to improve trade accuracy.

What was added
- trade_executor.py: A Decimal-first trade executor with:
  - Quantization of prices and amounts to symbol increments (round down)
  - Idempotent-friendly order params
  - TWAP slicing helper
  - Reconciliation helper to fetch fills as Decimals
- tests/test_trade_executor.py: pytest-based tests using a DummyExchange to validate quantization and TWAP splitting
- requirements.txt: suggested test/runtime deps

Why
- Floating point introduces rounding errors and can lead to invalid orders or incorrect accounting. Using Decimal and enforcing symbol increments makes orders deterministic and auditable.

How to run tests
1. Create a virtualenv and install deps: pip install -r requirements.txt
2. Run pytest

Integration notes
- Adapt the `create_order` / `fetch_order` calls to your exchange SDK (ccxt, exchange-specific client) and ensure idempotency is passed via headers/params if supported.
- Persist Decimals as strings or integer atomic units (cents, satoshis) in your database for exact accounting.

If you'd like, I can open a PR that integrates this TradeExecutor into your existing order flow and replace float-based math across the codebase. Tell me which files handle order placement and balance updates and I'll wire this in.
