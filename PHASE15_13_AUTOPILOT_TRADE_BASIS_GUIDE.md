# Phase 15.13 — Autopilot Trade Basis / Reason Card

This upgrade prints the reason behind every selected autopilot trade before Blue tries to send the MT5 order.

## What changed

When `autopilot on` is running, Blue still scans all symbols, but now the selected eligible candidate prints:

```text
AUTOPILOT TRADE BASIS / WHY BLUE SELECTED THIS SETUP
Symbol        : GOLD
Signal        : SELL
Auto action   : SELL
Confidence    : 85%
Grade         : A
Auto filter   : PASS
Entry plan    : entry ... | SL ... | TP1 ... | TP2 ...

TRADE BASIS / REASON CARD
Final decision : SELL SETUP FOUND | Confidence: 85%
Main basis     : Blue selected SELL because multi-timeframe direction, SMC/price-action context, and risk plan are aligned enough for the current mode.
Entry basis    : TF 5m | Session london | Regime bearish
Risk plan      : Entry | SL | T1 | T2 | RR | Lot
Why trade      :
  + 1h bearish score...
Warnings       :
  ! 5m mixed...
Filters checked:
  - News/Macro
  - Candlestick
  - Dataset ML
  - A+ filter
```

## Settings

In `config.py`:

```python
AUTOPILOT_SHOW_TRADE_BASIS = True
AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS = False
```

Use `AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS = True` only if you want a full reason card for every scanned BUY/SELL signal. It can make the terminal very long.

## Commands

```text
connect mt5
autopilot on
```

Blue will show:

- signal direction
- confidence
- grade
- ML score
- entry/SL/TP plan
- why the setup was selected
- warnings
- filters checked
- then order execution result

This is still demo-safe by default.
