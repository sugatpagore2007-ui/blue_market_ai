# Phase 15.9 — Autopilot Signal Display Hotfix

This hotfix fixes the confusing autopilot output where Blue showed only `WAIT` even when the market analysis had a BUY or SELL direction but strict execution filters blocked auto-entry.

## What changed

Blue now separates two things:

```text
SIGNAL = market direction Blue detected
AUTO   = whether autopilot is allowed to execute
```

## New output format

```text
GOLD: SIGNAL BUY | auto WAIT | confidence 84% | grade A | ML 82.4% | A+ BLOCK | block reason: grade A is below A+
EURUSD: SIGNAL SELL | auto WAIT | confidence 83% | grade A+ | A+ BLOCK | block reason: confidence below 85
USDJPY: SIGNAL BUY | confidence 88% | grade A+ | A+ PASS
```

## Meaning

- `SIGNAL BUY` or `SIGNAL SELL` means Blue has a directional setup.
- `auto WAIT` means autopilot is not taking the trade because a safety rule blocked auto execution.
- `A+ BLOCK` shows the exact reason, such as low confidence, below-A+ grade, no-trade brain, ML block, or voting rejection.

## Why this is safer

Blue can still tell you the signal direction, but it will not force automatic entries when filters reject the setup. This keeps the autopilot strict while making the terminal output easier to understand.

## Recommended usage

```text
autopilot on
win rate
best
gold
why
```

If you want to see trade basis for one pair, use:

```text
gold
why
```

Live/real trading is still controlled by your execution settings.
