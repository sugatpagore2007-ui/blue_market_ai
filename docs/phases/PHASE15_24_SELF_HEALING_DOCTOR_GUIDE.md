# Phase 15.24 — Self-Healing Doctor

This upgrade adds a safe diagnosis and repair layer.

## What it does automatically

When Blue starts, it checks and safely repairs local project basics:

- missing folders like logs/, reports/, datasets/, models/
- missing self-healing state file
- missing optional packages warning
- runtime error logging

## What it does during order execution

If an order does not punch, Blue now:

- keeps the exact MT5 retcode / last_error visible
- logs the order issue in `logs/blue_self_healing.log`
- prints a clear self-healing note in terminal
- suggests the exact next check, like `order doctor gold`

## What it will not do

Blue will not silently change risky things like:

- real account execution setting
- lot size / risk percent
- broker account login
- MT5 Algo Trading setting
- market hours

For these, Blue shows the problem in terminal.

## New commands

- `blue doctor`
- `doctor`
- `health check`
- `system check`
- `self heal on`
- `self heal off`

## Best command when order fails

```text
order doctor gold
```

or for any symbol:

```text
order doctor eurusd
order doctor usdjpy
order doctor btc
```
