# Blue Forex AI — Systematic Phase 16.2 Package

This package reorganizes the project into one cleaner production folder. All phase guides are collected in `docs/phases/`, while code paths remain backward-compatible so existing imports and commands keep working.

Start with `START_HERE_SYSTEMATIC.txt`.

---

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

See `START_HERE_FINAL.txt` and `docs/COMMANDS_AND_MEANINGS.md` for quick use.


## Phase 15.14 — MT5 Chart Data Engine

Blue can now use MT5 broker candles for chart analysis, so the data used for signals can match the broker used for execution.

New commands:

```text
data source
use mt5 data
use yahoo data
use auto data
mt5 candles gold
compare data gold
```

Recommended for demo autopilot:

```text
connect mt5
use mt5 data
mt5 candles gold
autopilot on
```

Default mode is `auto`: MT5 first, Yahoo/yfinance fallback if MT5 is unavailable.

## Phase 15.15 — Order Execution Doctor

Added read-only MT5/autopilot execution diagnosis.

Commands:

```text
order doctor
execution doctor
why no order
order doctor gold
execution doctor eurusd
order check btc
```

The doctor checks config flags, MT5 connection, demo guard, algo-trading status, broker symbol mapping, spread, volume limits, stops/freeze levels, daily guards, existing positions, and a safe `order_check()` dry-run. It does not call `order_send()`.


## Phase 15.16 — Internet / Environment Learning Brain

Blue can now learn public market context from trusted internet/RSS sources using commands like `internet seed`, `internet learn`, `internet report`, and `baby brain`. This memory is safe: it supports explanations and no-trade context only, and it cannot place orders or bypass autopilot/MT5 guardrails. See `PHASE15_16_INTERNET_LEARNING_BRAIN_GUIDE.md`.


## Phase 15.17 — Auto Everything + Text Command Mode (retained)

Run:

```bash
python main.py
```

Blue now starts the important background systems automatically:

- background learning
- internet/environment learning
- autopilot scanner
- auto manager through autopilot cycles
- text command terminal remains active

Basic control commands:

```text
status
basic commands
full auto on
full auto off
auto now
stop
order doctor gold
broker
connect mt5
balance
risk
help
exit
```

Safety: Blue still does not open MT5. Keep MT5 already open and logged in. Auto execution is demo-only by default and still passes all risk/broker filters before any order is sent.


## Phase 15.18 — Parallel Voice + Text Commands

Blue now keeps the existing command names and supports voice + typed commands together.
Type `voice`, `talk`, `voice text on`, `dual mode`, or `parallel mode` to start non-blocking voice listening.
The terminal prompt stays active, so you can type commands while Blue listens.
Use `voice text status` to check the listener.
See `PHASE15_18_PARALLEL_VOICE_TEXT_COMMANDS_GUIDE.md` for the full command list.


## Phase 15.19 — Neural Network Brain + Order Punch Shield
- New neural commands: neural help, neural train, neural report, neural predict gold, neural on/off.
- Best model: CNN + BiLSTM + Attention with TensorFlow; fallback MLP if TensorFlow is missing.
- Order Punch Shield adds order_check before order_send, price refresh, filling-mode fallback, and clearer MT5 diagnostics.
- Old commands are kept unchanged.

## Phase 15.21 — Natural Intent + Clean Terminal

Blue now understands normal language in text/voice, while all old commands still work.
Example: `what is gold doing today`, `protect my gold trade`, `find best trade`, `why gold not executing order`.

Terminal output is now cleaner and organized into readable cards.
See: `PHASE15_21_NATURAL_INTENT_CLEAN_TERMINAL_GUIDE.md`.

## Phase 15.22 — Self Learning Flywheel + Session Trade Quota

Added self-learning profitability flywheel and daily session quota.

Commands:

- `self learn`
- `self report`
- `profitability report`
- `mistake report`
- `calibrate confidence`
- `session quota`

Auto trading quota:

- 2 trades/day max
- 2 trades/day total
- London session: max 1 trade
- New York session: max 1 trade if London already traded
- New York session: max 2 trades if London did not trade



## Phase 15.22 Major Watchlist Update

Default major focus: xauusd, xagusd, ethusd, btcusd, usoil, usdjpy, eurusd, ustec, gbpusd. Other supported symbols remain minor/additional by command.

## Phase 15.24 — Self-Healing Doctor

Blue now runs a startup self-check and creates missing safe folders automatically. Runtime/code/order errors are logged to `logs/blue_self_healing.log` and shown clearly in terminal.

Commands:

```text
blue doctor
doctor
health check
system check
self heal on
self heal off
```

For execution issues, use:

```text
order doctor gold
```

## Phase 15.25 — Background Trade Manager

Autopilot now prints an immediate clean order card after a trade is punched and starts the auto manager in background. Terminal commands remain usable during autopilot.

Voice does not auto-start. Type `voice` to start voice.


## Phase 15.26 — London-to-New-York Rollover Quota

Final autopilot quota rule:

- Maximum daily auto entries: **2**
- London session: **maximum 1 trade**
- New York session: **1 trade if London already traded**
- New York session: **up to 2 trades if London did not trade**
- Auto manager remains active after entries
- Voice still starts only when command `voice` is typed

Use `session quota` to see live quota status.


## Phase 15.27 — Gold Reserved Quota
- Max 2 auto trades/day total.
- 1 daily slot reserved for Gold/XAUUSD only.
- 1 daily slot reserved for other instruments.
- Gold slot requires A+ setup or 100% confidence.
- If London has no trade, New York can still take only these same 2 slots.

## Phase 16 — Cognitive Architecture Auto Brain

Blue now starts a Cognitive Architecture background worker automatically.
It builds world model memory, market DNA, experience replay notes, verification queue and opportunity ranking hints.
Voice still starts only by command.

## Phase 16.1 — CME Group Institutional Data Brain

Blue now starts an automatic CME Group institutional context worker.
It maps XAUUSD/GC, XAGUSD/SI, USOIL/CL, USTEC/NQ, EURUSD/6E, GBPUSD/6B, USDJPY/6J, BTCUSD/BTC, and ETHUSD/ETH.

CME context is confirmation/filter only. It never directly punches orders and never bypasses Order Punch Shield.

Commands: `cme status`, `cme refresh`, `cme on`, `cme off`.

## Phase 16.2 — Autonomous Evolution Engine

Blue now runs an automatic evolution layer in the background and inside autopilot.
Autopilot scans every 5 minutes, generates evolution pulses during scan cycles, keeps the terminal free, and creates Monday weekly reports automatically.

Current daily rule: max 2 trades/day = 1 Gold slot + 1 other-pair slot across London/NY. If London gives no valid trade, NY can still take only the same two slots.

Guide: `PHASE16_2_AUTONOMOUS_EVOLUTION_ENGINE_GUIDE.md`
#   B l u e  
 