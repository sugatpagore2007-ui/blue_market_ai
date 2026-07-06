# Phase 15.11 — Autopilot Symbol Fallback Hotfix

## What was wrong

Autopilot was finding valid BUY/SELL signals, but it selected the strongest ranked setup first. In the shown case, NASDAQ was chosen, then MT5 could not select the broker symbol `NAS100m`.

Old behavior:

```text
Chosen autopilot trade: NASDAQ BUY
AUTO TRADE SKIPPED: Could not select MT5 symbol NAS100m
```

Then the cycle stopped without trying the next valid setup.

## What changed

Phase 15.11 keeps scanning/ranking normally, but during execution it now tries eligible candidates one by one until an order is actually sent or all candidates fail.

Example:

```text
Chosen autopilot candidate #1: NASDAQ BUY
AUTO TRADE SKIPPED: Could not select MT5 symbol NAS100m
Chosen autopilot candidate #2: USOIL SELL
AUTO TRADE DONE
```

## Added broker symbol fallbacks

Added more common aliases for index symbols:

```text
NAS100m, NAS100, USTECm, USTEC, US100m, US100, NAS100.cash, USTEC.cash, US100.cash
US500m, US500, SPX500m, SPX500, SP500m, SP500, SPXm, SPX
```

## How to run

```bash
python main.py
```

Inside Blue:

```text
connect mt5
autopilot on
```

## If an index still fails

Your broker may use a custom index name. Check available symbols:

```text
show mt5 symbols nas
show mt5 symbols us
show mt5 symbols sp
```

Then update `MT5_SYMBOL_MAP` in `config.py` if needed.

## Safety

This build is still demo-first:

```python
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
```
