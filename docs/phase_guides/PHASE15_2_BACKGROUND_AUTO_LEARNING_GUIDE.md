# Phase 15.2 — Background Auto Learning Guide

Phase 15.2 upgrades Blue from **startup-only learning** to a real **background learning worker**.

When you run:

```bash
python main.py
```

Blue now starts the terminal immediately and also launches a background worker. The worker keeps checking for new learning data while you continue using Blue.

## What runs in the background

The background worker safely checks these sources:

1. Blue journal/demo closed trades
2. MT5 closed trade history from the recent history window
3. Backtest CSV files in `reports/`
4. Backtest CSV files in `reports/auto_learn/`

It imports only **new unseen rows** and stores duplicate keys in:

```text
phase15_processed_learning_keys.json
```

So Blue does not learn the same old trade again every time it starts.

## What it does not do

The background learning worker is read-only for trading accounts.

It does **not**:

- place live trades
- close trades
- move SL/TP
- modify broker positions
- make ML place trades by itself

It only imports learning rows and may retrain the dataset model when enough new rows are available.

## New settings in `config.py`

```python
PHASE15_BACKGROUND_AUTO_LEARN_ENABLED = True
PHASE15_BACKGROUND_LEARN_ON_START = True
PHASE15_BACKGROUND_START_DELAY_SECONDS = 2
PHASE15_BACKGROUND_INTERVAL_SECONDS = 300
PHASE15_BACKGROUND_PRINT_UPDATES = False
PHASE15_BACKGROUND_STATUS_FILE = "phase15_background_learning_status.json"
```

Recommended default:

```python
PHASE15_BACKGROUND_AUTO_LEARN_ENABLED = True
PHASE15_BACKGROUND_INTERVAL_SECONDS = 300
PHASE15_BACKGROUND_PRINT_UPDATES = False
```

This checks every 5 minutes without disturbing your terminal.

## New commands

```text
background learn status
background learn now
background learn stop
background learn start
phase15 background status
```

## Useful command flow

Start Blue:

```bash
python main.py
```

Check background learning:

```text
background learn status
```

Force one learning pass:

```text
background learn now
```

Stop only the background worker for this session:

```text
background learn stop
```

Start it again:

```text
background learn start
```

## Auto retraining

The worker uses Phase 15 settings:

```python
PHASE15_AUTO_HISTORY_LEARNING_ENABLED = True
PHASE15_AUTO_RETRAIN_ENABLED = True
PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS = 25
```

Meaning:

- Blue keeps importing new rows in the background.
- It retrains only after enough new rows are found.
- If fewer rows are found, it waits instead of over-training on tiny updates.

## Status files

Blue writes background status here:

```text
phase15_background_learning_status.json
```

Main Phase 15 status is still here:

```text
phase15_auto_learning_status.json
```

## Best use

Keep MT5 open and logged in if you want MT5 history learning. If MT5 is closed, Blue skips MT5 and still learns from journal/backtest files.

Put backtest CSV files into:

```text
reports/auto_learn/
```

Then the background worker can import them during the next cycle.
