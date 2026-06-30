# Phase 15.10 — Demo Autopilot Working Mode

This hotfix is made for the issue where Blue shows `SIGNAL BUY/SELL` but does not send an order.

## What changed

Blue now separates signal quality from execution and enables **demo autopilot execution** by default:

```python
MT5_STAGE2_EXECUTION_ENABLED = True
AUTO_ORDER_EXECUTION = True
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
MIN_AUTO_TRADE_CONFIDENCE = 80
AUTOPILOT_MIN_SETUP_GRADE = "A"
```

## Why orders were not executing before

Previous builds required:

```text
confidence >= 85
setup grade A+
no economic-calendar block
execution enabled in config
```

So Blue could show a direction like `SIGNAL BUY`, but auto-entry stayed `WAIT`.

## What works now

When MT5 is connected to a demo account, Blue can auto-send the strongest eligible setup if:

```text
signal is BUY or SELL
confidence >= 80
setup grade >= A
MT5 is connected
account is demo
spread is inside limit
daily trade limit not reached
daily loss guard not triggered
no same-direction Blue position already open
```

## Run commands

```text
connect mt5
autopilot on
```

Check status:

```text
autopilot status
```

Stop:

```text
autopilot off
```

## Important safety

Real account auto-execution is still blocked:

```python
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
PHASE15_10_REAL_ACCOUNT_AUTO_EXECUTION_LOCK = True
```

Use this build for demo testing first. Live/real-money trading should only be enabled after legal checking, broker testing, and proper risk review.
