# Phase 16.1 — CME Group Institutional Data Brain

This upgrade adds CME Group futures context into Blue automatically.

## What it does automatically

When `python main.py` starts, Blue starts the CME Institutional Data Brain in the background.

It maps Blue symbols to institutional futures context:

- XAUUSD → GC Gold futures
- XAGUSD → SI Silver futures
- USOIL → CL Crude Oil futures
- USTEC → NQ Nasdaq futures
- EURUSD → 6E Euro futures
- GBPUSD → 6B British Pound futures
- USDJPY → 6J Japanese Yen futures
- BTCUSD → BTC Bitcoin futures
- ETHUSD → ETH Ether futures

## How it helps Blue

CME context helps Blue confirm whether the futures market supports the spot/CFD trade idea.

Example:

- Blue sees XAUUSD BUY.
- CME GC volume / open interest / bias supports gold strength.
- Blue can add small confirmation to confidence.

Or:

- Blue sees USOIL SELL.
- CME CL context is bullish.
- Blue treats it as divergence warning and reduces confidence slightly.

## Safety

CME data is advisory only.

It does not:

- punch orders by itself
- bypass Order Punch Shield
- bypass risk rules
- bypass Gold reserved quota
- override Autopilot safety

## Data access rule

Blue uses safe official/API or local file mode only.

- If you have an official CME/API endpoint, set `CME_API_URL` and optionally `CME_API_KEY`.
- If not, Blue uses `datasets/cme/cme_context_manual.csv` as a local snapshot template.
- Blue does not scrape protected CME pages.

## Commands

Old commands still work. New optional commands:

- `cme status`
- `cme refresh`
- `cme on`
- `cme off`

You do not need to type these during normal use; the background worker starts automatically.
