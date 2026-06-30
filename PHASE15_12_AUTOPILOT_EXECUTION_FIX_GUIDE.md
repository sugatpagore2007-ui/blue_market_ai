# Phase 15.12 — Autopilot Execution Fix

This build focuses on the problem where Blue shows valid signals but no demo order is punched.

## What changed

- Demo execution remains ON, real account execution remains blocked.
- Exness `Trial` servers are treated as demo/trial for the demo-only guard.
- Autopilot now uses a safer default symbol list first:
  - gold
  - eurusd
  - gbpusd
  - usdjpy
  - btc
  - eth
  - usoil
- Autopilot tries all eligible candidates until one demo order is actually sent.
- If a broker rejects the first order because of SL/TP/stops/filling, Blue retries the demo market order without SL/TP and then tries to attach SL/TP after the entry.
- More detailed execution diagnostics are printed in the terminal.

## How to run

```bash
python main.py
```

Inside Blue:

```text
connect mt5
autopilot on
```

## Required MT5 settings

MT5 must already be open and logged in.

In MT5, check:

1. Algo Trading button is ON.
2. Tools → Options → Expert Advisors → Allow algorithmic trading is ON.
3. The broker symbol exists in Market Watch.
4. The account is demo/trial.
5. Market is open for the selected symbol.

## If an order still does not punch

Read the exact line after `AUTO TRADE FAILED` or `AUTO TRADE SKIPPED`. It will usually say one of these:

- Auto execution blocked: account is not demo.
- Daily auto trade limit reached.
- Spread too high.
- Could not select broker symbol.
- Broker rejected order filling mode.
- Terminal trade is disabled / Algo Trading off.

This ZIP is still demo-only by default. Do not enable real-account automatic execution unless you understand the risk and legal rules.
