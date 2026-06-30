# Blue Forex Market AI — Phase 15.3 Ready ML Data Hotfix

# Blue Forex Market AI Phase 15.1 — Startup Auto Learning Final

This final build keeps Phase 9.2 code fixes, Phase 10 Human Trader Brain, Phase 11 Dataset ML Learning, Phase 12 Video Strategy Learning, Phase 13 Candlestick Intelligence, and Phase 14 Booming Bulls ML source learning. It now adds **Phase 15.1 Startup Auto Learning**, so Blue learns automatically every time you run `python main.py` by checking Blue journal/demo trades, MT5 closed trade history, and backtest CSV reports.


## Phase 15.1 Startup Auto Learning Added

Now Blue learns automatically when you start the app:

```bash
python main.py
```

At startup Blue will:

- Read new closed Blue journal/demo trades.
- Try to read new closed MT5 history from the last 30 days if MT5 is installed/running/logged in.
- Scan `reports/*.csv` and `reports/auto_learn/*.csv` for backtest CSV files.
- Ignore template/sample/example files.
- Skip duplicate trades using `phase15_processed_learning_keys.json`.
- Retrain only when the new-row threshold is reached.
- Never place trades from ML alone.

Startup output example:

```txt
Auto-learning startup: Startup auto-learning checked sources; imported 12 new ML rows.
```

Useful commands:

```txt
phase15 status
startup learn now
learning report
auto learn on
auto learn off
auto retrain on
auto retrain off
```

Settings are in `config.py`:

```python
PHASE15_STARTUP_AUTO_LEARN_ENABLED = True
PHASE15_STARTUP_LEARN_JOURNAL = True
PHASE15_STARTUP_LEARN_MT5 = True
PHASE15_STARTUP_LEARN_BACKTEST_REPORTS = True
PHASE15_STARTUP_MT5_HISTORY_DAYS = 30
PHASE15_STARTUP_HISTORY_TIMEFRAME = "5m"
PHASE15_STARTUP_BACKTEST_GLOBS = ["reports/*.csv", "reports/auto_learn/*.csv"]
```

To make backtest files auto-learn, place CSV reports here:

```txt
reports/my_backtest.csv
reports/auto_learn/my_backtest.csv
```

## Phase 15 Auto History Learning Added

Blue can now convert closed trade history into ML training rows automatically.

New commands:

```txt
phase15 status
startup learn now
learning report
auto learn on
auto learn off
auto retrain on
auto retrain off
retrain now
journal learn history
mt5 learn help
mt5 learn history 30d
mt5 learn history 90d
mt5 learn history all
mt5 learn history 30d 15m
backtest template
backtest learning help
backtest learn reports/my_backtest.csv
```

What Phase 15 does:

- Reads Blue's own closed journal/demo trades.
- Reads MT5 closed deals from the already-open MT5 terminal.
- Groups MT5 deals into completed trades.
- Labels trades as win/loss from profit or pnl/R result.
- Reconstructs session, trend/regime, ATR/spread and candlestick context from MT5 candles where possible.
- Converts backtest CSV reports into Blue's ML dataset format.
- Imports rows into the Phase 11 dataset table.
- Retrains the user dataset ML model when enough rows are available.
- Uses learned probability to approve/reduce/block future signals.

Read more: `PHASE15_AUTO_HISTORY_LEARNING_GUIDE.md`

## Important Safety Defaults

Phase 15 is read-only for history import. It does **not** place orders. ML can reduce confidence or block weak trades, but ML is not allowed to place live trades by itself. Keep demo mode and broker safety guards on while testing.

## Phase 13 Candlestick Intelligence Added

Blue now detects 50+ common candlestick patterns from OHLC candles and connects them to the signal engine.

New commands:

```txt
phase13 status
candle help
candlestick patterns
candles gold
candles eurusd 15m
```

Supported pattern families include:

- Single-candle: Doji, Long-Legged Doji, Dragonfly Doji, Gravestone Doji, Spinning Top, High Wave, Marubozu, Hammer, Hanging Man, Inverted Hammer, Shooting Star, Pin Bars, Belt Hold.
- Two-candle: Engulfing, Piercing Line, Dark Cloud Cover, Harami, Harami Cross, Tweezer Top/Bottom, Kicker, Matching Low, Meeting Lines, On-Neck, In-Neck, Thrusting, Separating Lines.
- Three+ candle: Morning/Evening Star, Morning/Evening Doji Star, Three White Soldiers, Three Black Crows, Three Inside/Outside Up/Down, Abandoned Baby, Rising/Falling Three Methods, Tasuki Gap, Ladder Bottom, Advance Block, Deliberation, Mat Hold.

Candlestick logic is conservative: it can confirm a trade, reduce confidence, warn against a trade, or convert a weak conflicting trade to WAIT. It never forces live orders by itself.

Read more: `PHASE13_CANDLESTICK_INTELLIGENCE_GUIDE.md`

## Phase 10 Upgrades Added

1. **Market Context Brain** — detects trend, choppy/ranging conditions, volatility, timeframe alignment, session context, and correlation notes.
2. **Human-Style Decision Pipeline** — every signal passes through market regime, HTF bias, liquidity/key levels, setup, entry trigger, SL, TP, risk check, and final trade/no-trade decision.
3. **Trade Memory Brain** — journal now stores setup type, regime, session, news risk, RR and outcome labels so Blue can learn which setups work.
4. **Auto ML Outcome Learning** — lightweight journal learner adjusts confidence before heavier Phase 9 hybrid ML has enough clean trade data.
5. **No-Trade Intelligence** — Blue can block trades when confidence, RR, timeframe alignment, context score, news risk or mode rules are not clean enough.
6. **News & Macro Brain** — converts Forex Factory/news and sentiment output into a macro risk score and manual calendar warning.
7. **Better Broker Intelligence** — broker symbol report maps Blue symbols to active MT5 broker symbols for Exness, XM, IC Markets, Pepperstone, Octa, FBS, HFM, generic MT5 and cTrader scaffold.
8. **Trader Personality Modes** — conservative, balanced, aggressive, and learning/paper mode.

## Important Safety Defaults

Blue still uses demo-first safety guards. Live execution should stay disabled until you have tested carefully on a demo account and checked local rules. cTrader remains scaffold-only unless you add real cTrader Open API authentication and execution.

## Run
```bash
pip install -r requirements.txt
python main.py
```


## One-command Autopilot

```txt
blue autopilot on      # starts everything in terminal-only mode
blue autopilot off     # stops the autopilot state
blue autopilot status  # shows current autopilot, auto execution, and manager settings
```

When `blue autopilot on` is used, Blue will:
- connect to MT5 if the terminal is already open and logged in
- scan all supported pairs in intraday mode
- use 5-minute entry logic while checking higher timeframes
- auto execute only if the signal passes the confidence threshold and guardrails
- manage open Blue trades automatically
- move SL to breakeven at 1R
- partial close at TP1
- trail stop after TP1
- close trade if an opposite signal appears
- stop trading when daily loss guard or max trade guard is hit
- log output in the VS Code terminal only

Blue does **not** open or pop up MT5 from code. Keep MT5 open manually. Demo-only protection is enabled by default.

## Main commands
```txt
check gold              # analyze one market
strongest               # scan strongest symbols
scanner                 # high-confidence market scanner
account                 # save balance/risk
journal                 # show open journal trades
close trade             # close/update journal trade
stats                   # win-rate and journal stats
backtest gold           # replay/backtest a symbol
screenshot <path>       # chart screenshot OCR analysis
detect chart <path>     # OpenCV visual chart detection base
voice                   # continuous voice mode, no need to say Blue every command
stop speaking           # interrupt voice reply
orb                     # floating orb status UI
live chart ocr          # OCR help
remember risk style is conservative
memory                  # saved preferences
phase10 status          # Human Trader Brain status
phase13 status          # Candlestick Intelligence status
phase15 status          # Auto History Learning status
learning report         # Phase 15 + dataset ML report
journal learn history   # Learn from Blue closed journal trades
mt5 learn history 30d   # Learn from MT5 closed deals
backtest learn reports/my_backtest.csv # Learn from backtest CSV
candlestick patterns    # Show supported candle pattern catalogue
candles gold            # Candle pattern report for gold 5m
candles eurusd 15m      # Candle pattern report for EURUSD 15m
trader modes            # show conservative/balanced/aggressive/learning modes
trader mode conservative # switch saved trader mode
trade memory            # outcome memory and learning report
broker intelligence     # active broker symbol mapping report
autonomous gold         # alert-only autonomous watch
exit
```

## Added upgrades
- Smart trade management AI: breakeven, partial profit, trailing-stop plan, invalidation rules
- Real LLM analyst brain: optional local Ollama `llama3.2:3b` explanation helper
- Self-learning confidence from past trades
- Psychology tracker before trade
- Real chart detection base using OpenCV
- Autonomous market scanner and alert-only assistant mode
- AI trade journal with win-rate tracking
- Replay/backtesting engine
- Advanced SMC/ICT concept labels: Judas swing, AMD, breaker, mitigation, IFVG, turtle soup, displacement, BPR, macro times, dealing range
- Liquidity engine and heatmap
- Human conversation mode with voice
- Interrupt + memory preferences
- Forex Factory news filter
- Sentiment engine for crypto Fear & Greed
- Autonomous AI trader framework in alert-only mode

## Optional APIs / services
- `yfinance`: market OHLCV data
- Forex Factory calendar page: news caution layer
- Alternative.me Fear & Greed API: crypto sentiment
- Ollama local API: optional LLM analyst brain

## Optional installations
For better voice output:
```bash
pip install pyttsx3
```

For local LLM brain:
```bash
# install Ollama from ollama.com, then:
ollama pull llama3.2:3b
```

For chart OCR, install Tesseract OCR on Windows and make sure it is in PATH.

## Safety note
This is educational software. It can be wrong. Always verify broker contract size, tick value, spread, leverage, economic news, and risk before any real trade.

## Phase 6.2 Smart Commands Fix

This fixed build adds a safer natural-language command parser and always asks for account balance + risk percent after analysis before lot-size calculation.

### New natural language examples
```txt
analysis gold
analyze gold and btc
scan market and check gold
check eurusd then show stats
take out win rate of btc
monitor gold and btc
backtest gold and eth
```

### Important behavior
- For every actionable signal, Blue asks account balance and risk percent again.
- You can give one command or multiple commands in one line.
- Blue understands related words like analyze, analysis, setup, signal, win rate, monitor, replay, and scanner.
- Psychology check is removed.


## Phase 7.1 — Human Voice Conversation Upgrade

Voice mode now feels more like a real analyst conversation, not only fixed commands.

Start it:
```txt
voice
```

Then speak naturally:
```txt
what do you think about gold
should I enter btc now
analysis gold and btc
why
what is the lot size
where is stop loss
what are targets
repeat that
short answer
detailed answer
stop speaking
```

What changed:
- one spoken response only, no duplicate voice reply
- remembers the last analyzed setup
- follow-up questions work: why, entry, SL, TP, lot size, repeat
- short / normal / detailed voice modes
- more human analyst style explanation
- still asks account balance and risk percent before calculating lot size

Voice output uses `pyttsx3`. If microphone input is unavailable, Blue falls back to typed commands so the app still opens.


## Trade style logic
Blue now defaults to **Intraday** trading. It scans all configured timeframes, but the final execution entry is planned from the **5-minute chart**.

Other styles activate only when you ask for them:
```txt
analyze gold                 # Intraday default, 5m entry
swing trading gold           # Swing mode
position trading btc         # Position mode
scalping eurusd              # Scalping mode
analyze gold and btc         # Multiple intraday commands
swing trading gold and btc   # Multiple swing commands
```

For every actionable trade, Blue asks account balance and risk percent before calculating lot size.


## MT5 Terminal-Only Integration

This version adds MT5 support without opening or popping the MT5 terminal from Python.
Keep MetaTrader 5 already open and logged in, then control everything from the VS Code terminal.

### Install
```bash
pip install MetaTrader5
```

### Stage 1 commands — recommended now
```txt
connect mt5
mt5 account
open positions
mt5 history
mt5 price gold
symbol spec gold
broker lot gold entry 2350 sl 2335 balance 1000 risk 1
```

Stage 1 can show:
- live prices
- account information
- open positions
- trade history
- broker symbol specification
- accurate lot size from broker tick value, tick size, and volume step

### Stage 2 commands — disabled by default
These commands exist but are protected. They only work after you set:
```python
MT5_STAGE2_EXECUTION_ENABLED = True
```
in `config.py`. They also ask you to type `EXECUTE` before sending any order.

```txt
buy gold lot 0.01 sl 2335 tp 2380
sell eurusd lot 0.05 sl 1.0900 tp 1.0800
modify position 123456 sl 2350 tp 2400
breakeven position 123456
partial close position 123456 lot 0.01
close position 123456
```

### Important
Blue does not auto-launch MT5. If `connect mt5` fails, open MT5 manually, log in, and try again.

## Auto MT5 Execution — No Confirmation Mode

This version can place MT5 orders automatically without asking for confirmation, but only when the guard rules pass.

Default guard rules in `config.py`:
```python
MT5_STAGE2_EXECUTION_ENABLED = True
AUTO_ORDER_EXECUTION = True
MIN_AUTO_TRADE_CONFIDENCE = 80
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_RISK_PERCENT = 1.0
MAX_AUTO_TRADES_PER_DAY = 3
MAX_DAILY_LOSS_PERCENT = 3.0
MAX_SPREAD_POINTS = 80
```

Auto execution flow:
```txt
analyze market -> confidence >= 80 -> demo account check -> daily loss check -> spread check -> broker lot calculation -> order send
```

Useful commands:
```txt
connect mt5
auto status
analyze gold
autonomous gold
open positions
```

Important: keep `AUTO_TRADE_DEMO_ONLY = True` while testing. This project is educational and can be wrong.

## Phase 7.5 — Auto Manager + Autonomous All Pairs

Added auto trade management after MT5 auto execution:

```txt
auto manager status      # show manager settings
auto manager on          # run one manager scan now
manage trades            # same as auto manager on
auto manager loop        # repeated manager checks
autonomous all pairs     # scan all supported pairs and manage trades
autonomous gold          # scan/manage one symbol
```

Auto manager can:
- move SL to breakeven at 1R
- partial close at TP1
- trail stop after TP1
- close trade if opposite signal appears
- stop managing/trading after daily loss guard triggers
- run autonomous scanning for all supported pairs

Important settings in `config.py`:

```python
AUTO_MANAGER_ENABLED = True
AUTO_MANAGER_DEMO_ONLY = True
AUTO_MANAGER_BREAKEVEN_AT_R = 1.0
AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1 = True
AUTO_MANAGER_PARTIAL_CLOSE_PERCENT = 50.0
AUTO_MANAGER_TRAIL_AFTER_TP1 = True
AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL = True
```

The manager is terminal-only and does not open MT5 from code. Keep MT5 already open and logged in.

Safety note: use demo testing first. Broker execution, spread, slippage, rejected orders, symbol names, and margin rules can change outcomes.

## Phase 7.6.1 — Exness suffix symbol fix

This build is configured for Exness-style symbols ending with `m`:

```txt
XAUUSDm, EURUSDm, GBPUSDm, USDJPYm, BTCUSDm, ETHUSDm
```

Blue also tries automatic symbol discovery if your broker uses slightly different names.

### Important terminal-only MT5 behavior
Blue will not launch or pop up MT5/Exness from code. MT5 must already be open and logged in before you run:

```txt
connect mt5
blue autopilot on
```

If MT5 is closed, Blue stops with a message instead of opening a terminal window.

If your broker does not use the `m` suffix, open `config.py` and change:

```python
MT5_SYMBOL_SUFFIX = ""
```


## MT5 fix notes

This build uses the same simple `mt5.initialize()` connection method that worked in your `test_mt5.py`. It also adds:

```txt
mt5 diagnose
show mt5 symbols
show mt5 symbols xau
show mt5 symbols eur
```

Blue still does not pass a terminal path or open charts. Keep MT5 open and logged in manually before using autopilot.

## Phase 7.6.4 — No MT5 Window Popup Upgrade

This build keeps MT5 terminal-only and reduces MT5/Exness window popups:

- Blue never launches MT5 or Exness from code.
- Blue reuses the existing MT5 API session instead of re-initializing on every autopilot cycle.
- On Windows, Blue tries to minimize MT5/Exness after connecting so it does not jump in front of VS Code.
- `mt5 diagnose` also avoids repeatedly popping MT5 when a connection is already active.

Config flags:
```python
MT5_SUPPRESS_WINDOW_POPUPS = True
MT5_MINIMIZE_AFTER_CONNECT = True
MT5_REUSE_EXISTING_CONNECTION = True
```

Use:
```txt
connect mt5
mt5 diagnose
blue autopilot on
```

## Phase 7.6.5 Fixes

### Gold / XAUUSDm order fix
Earlier, Gold could be skipped because the global spread guard was set to 80 points. Exness Gold (`XAUUSDm`) often has a larger point spread than forex pairs, so Blue now uses asset-specific spread limits:

- XAUUSDm / Gold: 450 points
- EURUSDm: 80 points
- GBPUSDm: 90 points
- BTCUSDm: 50000 points
- NAS100m: 800 points

Blue also uses the live MT5 bid/ask price for execution lot sizing instead of relying only on the analysis entry price.

### Autopilot terminal input fix
`blue autopilot on` now runs in a background thread. This means the VS Code terminal stays usable while autopilot scans.

You can now type commands while autopilot is running:

```txt
blue autopilot status
open positions
mt5 account
show mt5 symbols xau
blue autopilot off
```

### MT5 no-popup rule
Blue does not launch MT5 or Exness from code. Keep MT5 already open and logged in, then run:

```txt
connect mt5
blue autopilot on
```

## Phase 8.1 — Human AI Trading Desk + XAUUSDm Execution Fix

This build applies the Phase 8 human trading-desk upgrades directly into your uploaded Phase 7.6.5 project.

### Automatic AI Desk Logic
The following now work automatically in `check gold`, `scanner`, `blue autopilot on`, and voice replies:

- Multi-agent AI desk: market analyst, risk manager, liquidity agent, execution agent, research agent
- Market regime AI: trending, mixed, dealing-range, no-trade regimes
- Probability engine: estimated TP1/TP2/SL probability notes
- Trade quality grades: overall, setup, risk, liquidity, execution
- Institutional thesis: bias, liquidity target, invalidation, execution plan
- Portfolio risk note: warns about correlated exposure
- Market narrative: human-style analyst explanation
- Replay coach note: after-trade review guidance
- Research agent summary: sentiment/news context
- Scanner ranking by grade + confidence, not confidence only

### XAUUSDm / Gold Auto-Execution Fix
Gold orders can fail when the analysis feed uses Yahoo `GC=F` futures prices while MT5 execution uses broker `XAUUSDm` spot-style prices. This build fixes that by:

- Using live MT5 bid/ask for order price
- Rebuilding SL/TP around the live MT5 price while preserving signal risk distance and RR
- Keeping Gold-specific spread limits
- Avoiding duplicate same-direction Blue positions on the same symbol
- Trying MT5 filling-mode fallback if the broker rejects one filling type

### Autopilot Terminal Input
Autopilot still runs in a background thread, so you can type commands in the VS Code terminal while it runs:

```txt
blue autopilot on
blue autopilot status
open positions
mt5 account
show mt5 symbols xau
blue autopilot off
```

### Important
Keep MT5/Exness open manually and logged in. Blue does not launch MT5 and should not pop the MT5 window from code.

## Phase 8.2 — Controlled Pyramiding Upgrade

Blue can now scale into a winning trade using controlled pyramiding.

Commands:
```txt
pyramiding status
pyramiding on
pyramiding off
manage trades
blue autopilot on
```

Rules added:
- Blue only pyramids when the original trade is already in profit.
- Blue waits for breakeven protection before adding.
- Blue uses smaller add-on lot sizes.
- Blue blocks pyramiding if price is too far from the original entry.
- Default max distance is 2R from the original entry.
- Default max levels are 2 pyramid entries.
- Fresh signal must still agree with the original direction and meet the minimum confidence.
- Pyramiding is handled by the auto manager and works automatically during autopilot.

Config settings:
```python
PYRAMIDING_ENABLED = True
PYRAMID_MAX_LEVELS = 2
PYRAMID_ADD_AT_R = [1.0, 1.5]
PYRAMID_LOT_MULTIPLIERS = [0.50, 0.25]
PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R = 2.0
PYRAMID_MIN_CONFIDENCE = 85
PYRAMID_REQUIRE_BREAKEVEN = True
```

This prevents Blue from chasing price too far away from the original entry.


## Phase 8.3 — Best-Trade Autopilot + Breakeven Commands

### Best-trade-only autopilot
When you run:
```txt
blue autopilot on
```
Blue scans all supported pairs first, ranks the setups, and enters only the strongest A+ / high-confidence setup for that cycle. It no longer fires every valid signal from the scan.

Default rules in `config.py`:
```python
AUTOPILOT_ONLY_BEST_TRADE = True
AUTOPILOT_MIN_SETUP_GRADE = "A+"
AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE = 1
MIN_AUTO_TRADE_CONFIDENCE = 80
```

### Manual breakeven commands
You can type these while autopilot is running:
```txt
breakeven gold
breakeven xauusdm
breakeven btcusd
breakeven ethusd
breakeven eurusd
breakeven all
```
Blue will move SL to the entry price only for open positions that are already profitable. Losing or flat trades are skipped automatically.

## Phase 8.4 — Order Execution Truth + Guard Fix

This build fixes common reasons why Blue looked like it was sending an order but no order appeared in MT5.

Fixes:
- Blue now prints `AUTO TRADE DONE` only when MT5 returns a real success retcode.
- If MT5 rejects the order, Blue prints `AUTO TRADE FAILED` with `order_check`, `order_send`, retcode, and `mt5.last_error()` details.
- Daily trade limit now counts only new entry deals, not partial closes, breakeven changes, TP/SL exits, or manager actions.
- `AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE` is forced to `1`, so best-trade autopilot enters only the single strongest setup per cycle.
- MT5 popup suppression is turned back on.
- If price changes/requotes, Blue refreshes bid/ask and retries with extra deviation.

Commands to test:
```txt
connect mt5
mt5 diagnose
show mt5 symbols xau
open positions
auto status
blue autopilot on
```

If an order still does not execute, copy the full `AUTO TRADE FAILED` block from the VS Code terminal. It will now show the exact broker/MT5 rejection reason.


## Phase 8.5 — Multi-Broker Forex/CFD Adapter

This upgrade does **not** merge the Indian Market Blue project. Indian Market Blue remains a separate project.

Forex/CFD Blue now has a broker adapter layer so it is not locked to Exness only.

### MT5 broker profiles
```txt
broker status
broker set auto
broker set exness
broker set xm
broker set icmarkets
broker set generic_mt5
connect broker
connect mt5
show mt5 symbols xau
show mt5 symbols eur
symbol spec gold
```

### How to use with XM or another MT5 broker
1. Open that broker's MT5 terminal manually.
2. Log in to the correct demo account.
3. In Blue terminal run:
```txt
broker set xm
connect broker
mt5 diagnose
show mt5 symbols xau
show mt5 symbols eur
blue autopilot on
```

For any unknown MT5 broker:
```txt
broker set auto
connect broker
show mt5 symbols xau
show mt5 symbols eur
```
Blue will scan the broker's symbol list and try to match symbols automatically.

### cTrader note
cTrader does not work through the `MetaTrader5` Python package. This build includes a safe cTrader scaffold:
```txt
broker set ctrader
ctrader status
```
Real cTrader execution needs a separate cTrader Open API implementation with credentials, account id, symbol mapping, order placement, and position management.

### Important
- Exness, XM, IC Markets, Pepperstone etc. can work if they provide MT5.
- Keep MT5 open manually; Blue will not launch broker terminals.
- Use demo first.
- This is only for the Forex/CFD Blue project. Do not mix it with the Indian stock market Blue project.


## Phase 9 — Intelligence + Advanced Hybrid ML Upgrade

This version adds all 10 requested intelligence upgrades directly into the Forex/CFD Blue project. Indian Market Blue remains separate.

### Added automatically in every signal, scanner, voice explanation, and autopilot cycle
1. Trade Memory AI
2. Advanced Market Regime Detection
3. Economic Calendar / News Impact AI
4. Multi-Agent Voting
5. AI Chart Vision Hook
6. Session Intelligence
7. Correlation Engine
8. Advanced Hybrid ML Confidence Engine
9. A+ Setup Filter
10. Portfolio Manager AI

### Advanced Hybrid ML Engine
The ML layer is built as a hybrid ensemble:
```txt
Random Forest + XGBoost + LightGBM + CatBoost
```

It works in two modes:
- **Fallback mode**: before enough closed trade data exists, Blue uses a transparent heuristic ML score.
- **Trained mode**: after 40+ labeled win/loss trades exist in the journal/database, Blue trains the hybrid ensemble and uses the ensemble probability.

### New commands
```txt
phase9 status
ml status
ml train
```

### Autopilot behavior
`blue autopilot on` now scans all pairs and only allows trades that pass:
- confidence threshold
- A+ grade filter
- hybrid ML final score
- multi-agent voting
- news/calendar filter
- portfolio/correlation risk filter
- broker and spread guardrails

### Important
This improves trade filtering and decision quality, but it does not guarantee profit. Use demo testing and build a clean journal of closed wins/losses so the ML model can learn.

## Phase 9.1–9.5 — Automatic ML Learning From Real Outcomes

This build upgrades the Phase 9 ML system so Blue can learn from actual closed trade results.

### Added phases
```txt
Phase 9.1  Trade Data Collector
Phase 9.2  Hybrid ML Engine: Random Forest + XGBoost + LightGBM + CatBoost
Phase 9.3  Automatic retraining after new closed trades
Phase 9.4  ML trade rejection filter
Phase 9.5  Adaptive confidence from real win/loss outcomes
```

### New commands
```txt
phase9 status
ml status
ml report
ml train
ml auto retrain
```

### How learning works
1. Blue saves signals and journal trades.
2. You close/update trades as WIN or LOSS.
3. After 40+ labeled trades with both wins and losses, `ml train` trains the hybrid ensemble.
4. After training, every new signal receives:
   - rule confidence
   - ML win probability
   - final hybrid trade score
   - multi-agent approval
   - A+ autopilot pass/block reason
5. Autopilot blocks weak trades when ML/voting/news/portfolio filters do not agree.

### Important
ML improves filtering by learning which Blue setups performed best historically. It does not guarantee profit. Keep testing on demo and build a clean journal.

## Phase 9.2 Fix Build — Stability + Python 3.14 Safer Install

This fixed build keeps the Phase 9 auto-learning ML features but avoids common startup/install problems.

### Fixed in this build
- Project name/version now shows Phase 9.2 instead of old Phase 6 text.
- Real-account auto-trade flags are reset to safe mode:
```python
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
AUTO_MANAGER_ALLOW_REAL_ACCOUNT = False
```
- MT5 popup suppression is forced ON:
```python
MT5_SUPPRESS_WINDOW_POPUPS = True
MT5_MINIMIZE_AFTER_CONNECT = True
```
- Heavy ML libraries are now optional, not mandatory in the main `requirements.txt`.
- Use `requirements_ml_optional.txt` only after the app opens successfully.

### Install
```bash
pip install -r requirements.txt
```

Optional advanced ML:
```bash
pip install -r requirements_ml_optional.txt
```

If XGBoost, LightGBM, or CatBoost fail to install on your Python version, Blue still runs using the rule engine + fallback ML + RandomForest/Scikit-learn when available.

### Test
```txt
phase9 status
ml report
ml train
connect mt5
blue autopilot status
```

---

## Phase 11 — User Dataset ML Learning Brain

This upgrade lets Blue learn from a dataset that **you provide**. Instead of only learning from the built-in journal, Blue can now read CSV rows of past/demo trades, train a model, and use that trained probability when analyzing new setups.

### What this means

ML = giving Blue structured examples so it can learn patterns like:

- Which symbols perform better for your strategy
- Which sessions work best
- Which setup types fail often
- Which spread/news conditions are dangerous
- Which risk/reward profile performs better
- Whether liquidity sweep + FVG + trend alignment works better than random signals

Blue will not blindly copy the data. It converts the data into features, trains a model, and then gives a probability estimate for new trade setups.

### New files

```txt
learning/dataset_learning.py
models/                       # saved trained dataset model goes here
datasets/blue_ml_dataset_template.csv
datasets/blue_ml_sample_dataset.csv
```

### New commands

```txt
ml dataset help
ml dataset template
ml import dataset datasets/your_dataset.csv
ml train dataset datasets/your_dataset.csv
ml train imported dataset
ml dataset report
phase11 status
```

### Best CSV columns

Use this structure for best learning:

```csv
timestamp,symbol,timeframe,action,setup_type,trade_style,session,market_regime,trend_bias,news_risk,spread_pips,atr,rr_ratio,rule_confidence,tf_alignment,liquidity_sweep,fvg_present,order_block_present,smt_divergence,correlation_risk,entry,stop_loss,target_1,target_2,result,pnl_r,notes
```

### Required label

Every training row needs either:

```txt
result = win/loss
```

or:

```txt
pnl_r = positive number for win, negative number for loss
```

Examples:

```csv
XAUUSD,5m,BUY,liquidity_sweep_fvg,intraday,london,trend_expansion,bullish,normal,4,2.1,85,5,1,1,1,0,0,win,1.8
EURUSD,5m,SELL,breakout_retest,intraday,new_york,range_rotation,bearish,high,3,1.4,78,3,0,1,0,0,1,loss,-1.0
```

### How to train

1. Create the template/sample files:

```txt
ml dataset template
```

2. Put your real/demo tested rows into the template CSV.

3. Train:

```txt
ml train dataset datasets/your_dataset.csv
```

Or train the sample just to test the system:

```txt
ml train dataset datasets/blue_ml_sample_dataset.csv
```

4. Check status:

```txt
ml dataset report
```

### How it affects Blue signals

After a model is trained, every signal gets a new block:

```txt
User dataset ML engine:
Dataset probability 68.4% | Confidence 84% -> 78.5% | ALLOW
```

If the dataset probability is very low, Blue can block the signal and change it to WAIT:

```txt
BLOCK_LOW_DATASET_PROBABILITY
```

This is safer than forcing trades. The dataset model can **reduce or block weak setups**, but it never creates a live trade by itself.

### Important safety note

Dataset ML can improve filtering, but bad data creates bad learning. Do not train it with random, fake, or emotional trades. Best practice:

- Use demo/backtest trades first
- Label every row honestly as win/loss
- Include losses also, not only winning examples
- Use at least 20 rows for testing, 100+ rows for better learning, and 500+ clean rows for stronger patterns
- Keep live trading disabled until the model is tested properly



## Phase 12 — Video / Strategy Knowledge Learning

Blue can now store your YouTube strategy links, import your own notes or transcripts, extract trading lessons, and use those lessons as an advisory knowledge layer during analysis.

Commands:

```text
video learning help
video seed sources
video sources
video knowledge report
phase12 status
video import transcript <youtube_url_or_id> <path/to/transcript.txt>
video import notes <path/to/notes.md>
```

Important: links alone are saved as sources. For real learning, add transcript text or your own notes in `knowledge/transcripts/`, then import them. Blue stores extracted rules/lesson summaries, not full copied video content.

Read: `PHASE12_VIDEO_KNOWLEDGE_GUIDE.md`


## Phase 14 — Candlestick + Booming Bulls Knowledge ML

Added in this build:

- Candlestick-pattern intelligence is connected to the signal engine.
- Candlestick data is also available as ML features:
  - `candlestick_bias`
  - `candlestick_pattern`
  - `candlestick_strength`
- Booming Bulls channel source system is added safely:
  - source URL stored in `knowledge/booming_bulls_sources.json`
  - optional video URL discovery using `yt-dlp`
  - optional public-caption import using `youtube-transcript-api`
  - manual notes import supported
  - knowledge dataset export to `datasets/booming_bulls_strategy_knowledge.csv`

Commands:

```txt
phase14 status
booming bulls help
booming bulls seed
booming bulls fetch videos 50
booming bulls fetch transcripts 25
booming bulls import notes knowledge/my_booming_bulls_notes.md
booming bulls export dataset
booming bulls report
```

Copyright/safety note: Blue does not include copied full YouTube transcripts, videos, or paid course content. Use your own notes or public captions where available. Video lessons are a knowledge filter; actual predictive ML still needs win/loss trade data from demo trades or backtests.


### Phase 15 terminal reason card

Every analysis now prints `TRADE BASIS / REASON CARD` showing the final decision, entry basis, multi-timeframe reasons, warnings, filters checked, ML probability, and risk plan.

---

## Phase 15.3 — Ready ML Training Sets Included

This ZIP includes ready-made ML datasets inside the `datasets/` folder. You can train Blue immediately without creating your own CSV first.

Best first command inside Blue:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

Other included datasets:

```text
ml train dataset datasets/blue_ml_starter_150_rows.csv
ml train dataset datasets/blue_ml_candlestick_250_rows.csv
ml train dataset datasets/blue_ml_smc_ict_setups_250_rows.csv
ml train dataset datasets/blue_ml_backtest_style_250_rows.csv
ml train dataset datasets/blue_ml_mt5_history_style_150_rows.csv
```

Read:

```text
PHASE15_3_READY_ML_DATASETS_GUIDE.md
README_READY_ML_DATASETS.md
```

Note: These ready-made datasets are synthetic example data for testing how Blue learns. For real performance improvement, use your own demo trades, backtest reports, and MT5 closed history.


## Phase 15.3 Ready ML Data Hotfix

This package includes the ready ML datasets inside `datasets/` and fixes the candlestick-column training error.

Use:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

If you previously saw `candlestick_strength ... not in index`, this build fixes it.


## Clean One-Folder Layout

This package uses one top-level project folder: `Blue_Forex_Market_AI_Final_One_Folder`.

Phase guide files such as Phase 11, Phase 12, Phase 13, Phase 14, and Phase 15 guides are moved into:

```text
docs/phase_guides/
```

Important code folders like `analysis/`, `learning/`, `broker_bridge/`, `risk/`, `storage/`, and `utils/` are still kept as folders because Python needs that module structure to run correctly.

Start command:

```bash
python main.py
```

Train ready ML dataset:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

---

## Phase 15.4 — Friendly Short Commands

Blue now understands simple human commands. Type `help` in the terminal to see them.

Examples:

```text
gold
best
scan
train
learn
learn 90d
learning
model
connect
broker
safe
conservative
normal
fast
practice
go
stop
candles gold
patterns
bye
```

Old long commands still work, but you do not need to memorize them.

---

## Phase 15.4 Friendly Human Commands

This build adds a friendly command layer. Type `help` inside Blue to see the full simple command menu.

Examples:

```text
gold
best
train
learn on
learn status
use xm broker
connect my broker
breakeven gold
close half eur
trail btc
stop everything
```

Pair commands are generic. Replace `gold` with `eur`, `gbp`, `jpy`, `btc`, `eth`, `silver`, `oil`, `nasdaq`, or a broker symbol.

See `PHASE15_4_FRIENDLY_COMMANDS_GUIDE.md` for the full command table.

---

## Phase 15.6 — Always-On Voice + Text Commands

This build starts background voice automatically when you run:

```bash
python main.py
```

You can type commands in the terminal while Blue listens in the background.

Voice examples:

```text
hey blue check gold
hey blue show me best trade
hey blue train your brain
hey blue learn from history
hey blue move gold to breakeven
hey blue stop everything
```

Text examples:

```text
gold
best
train
learn status
voice background status
voice off
voice
```

More details: `PHASE15_6_ALWAYS_ON_VOICE_GUIDE.md`


## Phase 15.7 — Win Rate Intelligence

Blue now supports connected-account win-rate reports from both text and always-on voice.

Commands:

```text
win rate
connected account win rate
show my win rate
show everything
stats
performance
gold win rate
btc win rate
take out win rate of btc
win rate 30d
win rate gold 180d
win rate help
```

Voice examples:

```text
hey blue show my win rate
hey blue connected account win rate
hey blue take out win rate of btc
```

The report shows MT5 connected account history first, then Blue journal/demo memory, then imported ML dataset stats. It includes closed trades, wins/losses/breakeven, win rate, net profit, profit factor, average trade, symbol breakdown, direction breakdown, setup/session breakdown, and recent closed trades.

See `PHASE15_7_WIN_RATE_INTELLIGENCE_GUIDE.md`.


## Phase 15.9 — Compact Win Rate + Manual Voice

- `win rate`, `stats`, `performance`, and symbol win-rate commands now show only the connected MT5 account win-rate report in the clean terminal format.
- Blue no longer adds journal, ML dataset, recent trades, or extra help text to win-rate output.
- Voice does not auto-start when running `python main.py`. Type `voice` to activate background listening while text commands still work.

```text
win rate
gold win rate
take out win rate of btc
voice
voice off
voice background status
```


## Phase 15.9 — Autopilot Signal Display Hotfix

Autopilot now separates **market signal direction** from **execution permission**.

Example terminal output:

```text
GOLD: SIGNAL BUY | auto WAIT | confidence 84% | grade A | A+ BLOCK | block reason: grade A is below A+
```

Meaning:

- `SIGNAL BUY/SELL` = Blue's market read.
- `auto WAIT` = Blue is not allowed to enter automatically because the strict autopilot safety filters blocked it.
- Orders are still protected by confidence, A+ grade, ML, no-trade brain, spread guard, demo-only guard, and execution settings.

This fixes the confusing old output where every blocked setup looked like only `WAIT`.


## Phase 15.10 Demo Autopilot Working Mode

This build fixes the situation where Blue displayed `SIGNAL BUY/SELL` but did not execute because every setup was shown as `auto WAIT`. Demo execution is now enabled in config, while real-account auto trading remains blocked.

Use:

```text
connect mt5
autopilot on
```

Blue now requires confidence >= 80 and setup grade >= A for demo autopilot. News/macro risk is shown as a warning in this demo working mode, not a hard block. Real-account auto execution remains OFF/blocked by demo-only protection.

See `PHASE15_10_DEMO_AUTOPILOT_WORKING_GUIDE.md`.

## Phase 15.11 Autopilot Symbol Fallback

If the strongest setup uses an MT5 symbol that your broker does not provide, Blue now skips that instrument and tries the next eligible candidate instead of stopping the whole cycle.

Use:

```text
connect mt5
autopilot on
show mt5 symbols nas
show mt5 symbols us
```


## Phase 15.12 Autopilot Execution Fix

This build fixes the issue where Blue showed `SIGNAL BUY/SELL` but no demo order punched. Autopilot now tries all eligible candidates, treats Exness Trial servers as demo/trial for the demo guard, uses common Exness demo symbols first, and retries broker-rejected SL/TP orders with a safe no-SLTP-then-attach fallback.

Run:

```bash
python main.py
```

Then:

```text
connect mt5
autopilot on
```

See `PHASE15_12_AUTOPILOT_EXECUTION_FIX_GUIDE.md`.


## Phase 15.13 — Autopilot Trade Basis

Autopilot now prints a full `AUTOPILOT TRADE BASIS / WHY BLUE SELECTED THIS SETUP` card before trying to place the selected demo order. This shows the entry basis, SL/TP plan, confidence, grade, ML score, market context, warnings, and filters checked.

Commands:

```text
connect mt5
autopilot on
```
