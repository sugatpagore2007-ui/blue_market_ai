# Phase 15 — Auto History Learning Guide

Phase 15 lets Blue learn automatically from real examples instead of only manual CSV rows.

It can learn from:

1. Blue's own closed journal/demo trades
2. MT5 closed trade history
3. Backtest report CSV files

The learning flow is:

```txt
closed trade / backtest row
↓
Blue converts it into ML training columns
↓
Blue labels it win/loss from profit, result, or pnl_r
↓
Blue imports rows into the Phase 11 dataset table
↓
Blue retrains the dataset ML model when enough rows exist
↓
Future signals use dataset probability as an approve/block filter
```

## Important safety behavior

Phase 15 is read-only for importing history. It does not place orders. ML can reduce confidence or block a weak setup, but it should not be allowed to place live trades alone.

Safe defaults in `config.py`:

```python
PHASE15_AUTO_HISTORY_LEARNING_ENABLED = True
PHASE15_AUTO_RETRAIN_ENABLED = True
PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS = 25
PHASE15_LEARNING_CAN_BLOCK_TRADES = True
PHASE15_LEARNING_CAN_PLACE_TRADES = False
```

## Commands

### Status and reports

```txt
phase15 status
learning report
auto learn on
auto learn off
auto retrain on
auto retrain off
retrain now
```

### Learn from Blue's own journal

Use this after you close/update trades inside Blue's journal:

```txt
journal learn history
```

This reads closed trades from `blue_market_ai.db`, creates a dataset CSV in `datasets/`, imports those rows, and retrains when possible.

### Learn from MT5 closed trade history

Keep MT5 open manually and logged in first.

```txt
connect mt5
mt5 learn history 30d
mt5 learn history 90d
mt5 learn history all
mt5 learn history 30d 15m
```

Blue reads MT5 closed deals using the MetaTrader5 Python bridge, groups deals by position, labels profit as win/loss, reconstructs session/trend/candlestick context from candles where possible, exports CSV, imports it into ML, then retrains.

Best quality:

- Blue-created MT5 demo trades have better comments and context.
- Manual MT5 trades are still useful, but Blue must reconstruct setup from candles.
- If stop loss is missing in MT5 history, Blue uses sign-only pseudo-R (`+1` or `-1`) for `pnl_r`.

### Learn from backtest CSV

Create a template:

```txt
backtest template
```

Then fill or export your backtest report and run:

```txt
backtest learn reports/my_backtest.csv
```

Accepted column aliases include:

```txt
symbol / pair / instrument
action / side / type / direction
entry_time / open_time / time
entry_price / entry / open_price
sl / stop_loss / stop
tp / take_profit / target_2
exit_price / close_price
profit / pnl / net_profit
pnl_r / r_multiple / r_result
setup_type / strategy / pattern
session
market_regime
news_risk
candlestick_pattern
candlestick_bias
candlestick_strength
```

## Best data for strong ML

For weak testing:

```txt
20–50 labeled trades
```

For useful learning:

```txt
200+ labeled trades
```

For stronger learning:

```txt
1000+ labeled trades
```

Give both wins and losses. If you only give winning trades, Blue learns badly.

## What Blue learns

Blue learns patterns like:

```txt
Gold London liquidity sweep + bullish candle + low news risk = often good
EURUSD high-news sideways breakout = often bad
High spread + low RR + neutral candles = avoid
Specific broker symbols and sessions perform differently
```

Then future signals can show:

```txt
Dataset probability: 72%
Trade allowed.
```

or:

```txt
Dataset probability: 38%
Trade changed to WAIT.
```

## Terminal trade reason card

Every normal analysis and strongest scan now prints a clear reason card before the longer analyst explanation.

Example terminal output:

```txt
TRADE BASIS / REASON CARD
------------------------------------------------------------------------
Final decision : BUY SETUP FOUND | Confidence: 88%
Main basis     : Blue selected BUY because multi-timeframe direction, SMC/price-action context, and risk plan are aligned enough for the current mode.
Entry basis    : TF 5m | Session london | Regime bullish / discount
Risk plan      : Entry 2340.50 | SL 2335.00 | T1 2348.75 | T2 2354.25 | RR(T2) 2.5 | Lot 0.02
Why trade      :
  + 1h: bullish score 3 — EMA trend bullish, above 200 EMA, bullish bias inside discount
  + 15m: bullish score 2 — bullish CHOCH/BOS, liquidity sweep, RSI bullish momentum
Warnings       :
  ! 5m: mixed score 0.5 — EMA trend mixed
Filters checked:
  - News: checked | penalty 0 | no high impact warning loaded
  - Dataset ML: 72% probability | ALLOW
  - Candles: bullish | decision CONFIRM
------------------------------------------------------------------------
```

This helps you see **on what basis Blue is taking the trade**: timeframe confluence, SMC/liquidity, candle pattern, ML probability, news/macro filter, risk plan, and no-trade warnings.

## Recommended workflow

```txt
1. Run demo trades only.
2. Close/update trades normally.
3. Run: journal learn history
4. Connect MT5 and run: mt5 learn history 30d
5. Import backtests: backtest learn reports/my_backtest.csv
6. Check: learning report
7. Keep live trading disabled until you have tested heavily.
```


## Startup Auto Learning

Yes — Blue can learn whenever you run the code. In Phase 15.1, `main.py` automatically runs a startup learning routine before showing the `Blue >` prompt.

It checks:

1. Blue journal/demo closed trades
2. MT5 closed history from the last 30 days, if MT5 is connected/running
3. Backtest CSV files in `reports/*.csv` and `reports/auto_learn/*.csv`

It imports only new rows. Duplicate trades are skipped using `phase15_processed_learning_keys.json`.

Manual trigger:

```txt
startup learn now
```

Turn it on/off:

```txt
auto learn on
auto learn off
```

Retrain control:

```txt
auto retrain on
auto retrain off
retrain now
```

Startup learning is read-only. It never places or modifies orders.
