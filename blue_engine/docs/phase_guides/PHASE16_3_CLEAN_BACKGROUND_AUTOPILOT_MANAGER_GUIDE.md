# Phase 16.3 — Clean Background Autopilot Manager

This upgrade keeps Blue autopilot running in the background while the terminal stays clean and usable.

## What changed

- Autopilot still scans every 5 minutes.
- Main terminal remains free for text commands.
- Blue no longer prints messy full scan details for every symbol.
- It shows only important cycle summaries, execution errors, and new-order cards.
- When an order is punched, Blue immediately prints the trade card without waiting for the scan cycle to finish.
- Auto manager remains active in the background after entry.
- Manager output is printed only when something important happens, such as breakeven, partial close, trailing, close, TP/SL, or an error.

## Important cards shown

1. Autopilot active card
2. Short background scan summary
3. Immediate order-punched card
4. Important manager-action card
5. Error / failed order card

## Safety unchanged

- Order Punch Shield still controls execution.
- Gold reserved quota remains active.
- CME / evolution brains remain advisory.
- Voice auto-start remains off.
- Autopilot does not bypass risk/session/daily guards.

## Commands still work while autopilot runs

Examples:

```text
gold
status
trades
profit
manager
breakeven gold
close half gold
blue autopilot off
```
