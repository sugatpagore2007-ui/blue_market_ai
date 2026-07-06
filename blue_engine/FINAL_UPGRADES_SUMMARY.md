# Blue Forex Market AI — Final All Upgrades Build

This is the combined final build from the first Forex AI project through Phase 15.13.

## Included upgrade timeline

- Multi-broker MT5 adapter: Exness, XM, generic MT5 profiles, cTrader scaffold.
- Human Trader Brain: market context, no-trade intelligence, trade memory, trader modes.
- Dataset ML Learning: manual CSV learning, ready ML datasets, dataset probability in signals.
- YouTube Strategy Learning: transcript/notes based strategy knowledge importer.
- Candlestick Intelligence: built-in candlestick features and optional TA-Lib pattern scanning.
- Booming Bulls source learning: channel/source notes importer for strategy knowledge.
- Auto History Learning: learn from Blue journal/demo trades, MT5 history, and backtest CSVs.
- Startup + Background Learning: automatic learning while Blue runs.
- Ready ML Data: included training CSVs and Excel workbook.
- Friendly Commands: short commands and human-language command routing.
- Voice Control: manual background voice listener with typed commands still working.
- Win Rate Intelligence: compact connected MT5 account win-rate report.
- Demo Autopilot Working Mode: demo-only auto execution settings.
- Symbol Fallback: tries alternate broker symbol names if one symbol fails.
- Autopilot Execution Fix: retries and prints execution diagnostics.
- Autopilot Trade Basis: prints why Blue selected a setup before execution.

## Run

```bash
python main.py
```

## First setup

```text
connect mt5
voice status
win rate
train
autopilot on
```

## Demo autopilot test flow

1. Open MT5 manually and login to demo/trial account.
2. Turn on Algo Trading in MT5.
3. Run `python main.py`.
4. Type `connect mt5`.
5. Type `autopilot on`.

## Important safety defaults

- This build is intended for demo testing first.
- Real-account automatic execution remains blocked by default.
- MT5 must already be open; Blue does not launch/pop up MT5.
- ML can help approve/block trades but does not guarantee profit.

## Key files

- `main.py` — main terminal app
- `config.py` — settings and safety guards
- `datasets/` — ready ML datasets and templates
- `docs/` — commands and phase guides
- `presentation/` — PPT files
- `requirements.txt` — core packages
- `requirements_voice.txt` — voice packages
- `requirements_ml_optional.txt` — optional ML packages


## Phase 15.14 — MT5 Chart Data Engine

- Added MT5 broker candle data source.
- Added data source modes: `auto`, `mt5`, `yahoo`.
- Added commands: `data source`, `use mt5 data`, `use yahoo data`, `use auto data`, `mt5 candles gold`, `compare data gold`.
- Blue signal output now shows whether chart data came from MT5, Yahoo, or Yahoo fallback.
- Recommended autopilot flow now uses MT5 chart data first so analysis and execution use the same broker feed.


## Phase 15.15 Order Execution Doctor

Commands:

```text
order doctor
execution doctor
why no order
order doctor gold
execution doctor eurusd
order check btc
```

This is read-only. It diagnoses why MT5/autopilot may not punch an order and never places trades by itself.


## Phase 15.16 — Internet / Environment Learning Brain

Blue can now learn public market context from trusted internet/RSS sources using commands like `internet seed`, `internet learn`, `internet report`, and `baby brain`. This memory is safe: it supports explanations and no-trade context only, and it cannot place orders or bypass autopilot/MT5 guardrails. See `PHASE15_16_INTERNET_LEARNING_BRAIN_GUIDE.md`.

## Phase 15.25 — Background Trade Punch Notification + Always-Active Manager

Added immediate clean terminal order card after autopilot punches a trade, without waiting for the whole scan cycle to finish. Autopilot also starts the auto manager background service, so open Blue trades are managed continuously while the terminal remains available for text commands.


## Phase 15.26 — London-to-New-York Rollover Quota

Changed autopilot quota to final requested rule:

- 2 auto trades per day maximum
- London can take max 1 trade
- If London traded, New York can take 1 trade
- If London did not trade, New York can take 2 trades
- Voice auto-start remains OFF
- Background auto manager remains active after entries


## Phase 15.27 — Gold Reserved Quota
- Max 2 auto trades/day total.
- 1 daily slot reserved for Gold/XAUUSD only.
- 1 daily slot reserved for other instruments.
- Gold slot requires A+ setup or 100% confidence.
- If London has no trade, New York can still take only these same 2 slots.

## Phase 16 — Cognitive Architecture Auto Brain

Added automatic background cognitive layer:
- World Model
- Market DNA
- Experience Replay
- Verification Queue
- Opportunity Ranking
- Confidence Calibration Tasks

Runs automatically after `python main.py`. No command needed.
Safety: advisory only; does not bypass Order Punch Shield or risk filters.

# Phase 16.2 — Autonomous Evolution Engine

Added automatic Monday reports, 5-minute autopilot scans, autopilot evolution pulse, post-order reflection seed, market DNA, source trust, verified-learning promotion pipeline, and confidence calibration foundation. Works automatically and also inside autopilot.


# Phase 16.3 — Clean Background Autopilot Manager

Added clean non-blocking autopilot terminal mode. Autopilot runs every 5 minutes in the background, prints only important cycle summaries, shows immediate order-punched cards, and keeps auto trade manager active after entries.
