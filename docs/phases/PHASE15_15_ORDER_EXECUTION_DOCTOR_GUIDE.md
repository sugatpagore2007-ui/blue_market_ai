# Phase 15.15 — Order Execution Doctor

This upgrade adds a read-only doctor that explains why Blue/MT5 may not punch an order.

## New commands

```text
order doctor
execution doctor
why no order
order doctor gold
execution doctor eurusd
order check btc
trade doctor gold
```

## What it checks

- MT5 package and terminal connection
- MT5 account login/server/balance
- Demo/trial detection for demo-only guard
- Algo trading / terminal trade allowed flags
- Blue config execution switches
- Symbol mapping and broker symbol selection
- Live bid/ask tick availability
- Spread against Blue's configured limit
- Stops/freeze levels
- Broker volume min/step/max
- Daily trade limit and daily loss guard
- Existing same-direction Blue positions
- Optional broker `order_check()` dry-run

## Safe behavior

The doctor is read-only. It does not call `order_send()` and does not place, close, or modify trades.

## Recommended flow

```text
connect mt5
use mt5 data
order doctor gold
autopilot on
```

If an order still does not execute, run:

```text
why no order
order doctor gold
```

Blue will print exact blockers such as:

```text
ORDER WOULD NOT EXECUTE
Blockers:
  - AUTO_ORDER_EXECUTION is OFF in config.py
  - Terminal Algo Trading is OFF / trading not allowed
  - Broker symbol could not be selected: XAUUSDm
  - Spread too high: 620 points > 450
```
