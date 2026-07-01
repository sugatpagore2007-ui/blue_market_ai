# Phase 15.16 — Internet / Environment Learning Brain

This upgrade gives Blue a safe “learn from internet/environment” layer, like a baby learning by observing the world.

## What was added

- `knowledge/internet_learning.py` — safe internet/RSS learning module.
- `knowledge/internet_sources.json` — source list created by `internet seed`.
- `knowledge/internet_learning_memory.jsonl` — long-term note memory.
- `datasets/blue_internet_knowledge_dataset.csv` — exported knowledge dataset.
- `reports/internet_learning_report.md` — readable learning report.
- Optional background learning integration inside `learning/background_auto_learning.py`.
- Friendly commands added in `main.py` and `utils/command_parser.py`.

## Safety rule

Internet learning is **context only**.

It can help Blue explain:

- macro risk,
- USD strength/weakness,
- gold safe-haven mood,
- inflation/rate pressure,
- general market environment,
- why a trade should be avoided.

It cannot:

- place trades by itself,
- bypass autopilot filters,
- override MT5 execution guardrails,
- change SL/TP without trade-management commands,
- trust unknown websites automatically.

## Commands

```text
internet help       -> show Internet Learning Brain help
internet seed       -> add default trusted sources
internet sources    -> show the source list
internet add <url>  -> add your own source
internet learn      -> learn from internet now
environment learn   -> same as internet learn
internet report     -> show what Blue learned
baby brain          -> explain the human-like learning model
internet on         -> enable internet learning + background internet mode
internet off        -> disable internet learning
```

## How to use first time

```bash
python main.py
```

Then inside Blue terminal:

```text
internet seed
internet learn
internet report
baby brain
```

## Background learning

By default, internet background learning is OFF to avoid unnecessary scraping/data usage.
Turn it on manually:

```text
internet on
```

When enabled, Blue’s background learning loop checks internet learning only when due. The default minimum gap is 6 hours.

## Config settings

In `config.py`:

```python
PHASE15_16_INTERNET_LEARNING_ENABLED = True
PHASE15_16_INTERNET_BACKGROUND_LEARN_ENABLED = False
PHASE15_16_INTERNET_MIN_HOURS_BETWEEN_RUNS = 6
PHASE15_16_INTERNET_MAX_ITEMS_PER_SOURCE = 8
PHASE15_16_INTERNET_REQUEST_TIMEOUT_SECONDS = 12
PHASE15_16_INTERNET_ALLOW_UNTRUSTED_SOURCES = False
```

## Human-like learning pipeline

1. **See** — read MT5 candles, closed trades, backtests, videos, and internet sources.
2. **Notice** — tag concepts like USD, inflation, rates, gold, risk mood, liquidity.
3. **Remember** — save observations with source/time/tags and duplicate protection.
4. **Practice** — compare ideas with actual closed trades and backtests.
5. **Decide safely** — use learned context only after risk filters, broker filters, and signal rules.
