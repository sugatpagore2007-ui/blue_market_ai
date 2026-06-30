# Phase 15.17 — Auto Everything + Text Command Mode

This upgrade makes Blue start the important systems automatically when you run:

```bash
python main.py
```

## What starts automatically

- Background learning service
- MT5/journal/backtest history learning checks
- Internet/environment learning background mode
- Autopilot background scanner
- Auto manager inside autopilot cycles
- Terminal text command loop stays active

Blue still does **not** open MT5 by itself. Keep MT5 open manually, logged in, and Algo Trading enabled.

## Basic commands

```text
status
basic commands
full auto on
full auto off
auto now
stop
order doctor gold
broker
connect mt5
balance
risk
voice
help
exit
```

## Manual commands still work

```text
gold
eurusd
btc
best
scan
why
win rate
internet report
manager
autopilot
```

## Safety

Automatic mode is demo-only by default:

```text
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
BLUE_AUTO_FORCE_DEMO_ONLY = True
```

Internet learning and ML can support context and explanations, but they do not directly place trades. Orders still need to pass:

- MT5 connection
- Demo account guard
- Symbol mapping
- Spread guard
- Confidence threshold
- Setup grade filter
- Daily trade/loss limits
- Duplicate trade checks
- Order doctor / broker mechanics

## What this upgrade solves

Earlier Blue needed many commands after startup. Now Blue behaves more like an automatic assistant:

1. Run Blue once.
2. It starts learning and scanning.
3. You can still type commands anytime.
4. Basic commands act like control buttons.
5. Autopilot still explains why a trade was selected or blocked.
