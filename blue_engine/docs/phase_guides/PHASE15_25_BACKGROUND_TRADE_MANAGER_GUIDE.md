# Phase 15.25 — Background Trade Punch Notification + Always-Active Manager

This upgrade keeps Blue usable while autopilot works in the background.

## What changed

- Autopilot still scans in a background thread.
- Terminal stays free so you can type commands anytime.
- When autopilot punches a new trade, Blue immediately prints a clean order card.
- Blue does not wait until the full autopilot cycle ends to show the trade details.
- After a trade is punched, Blue immediately runs the trade manager once.
- Blue also starts an always-active background auto manager with autopilot.

## Auto manager actions

The always-active manager can manage Blue trades with:

- breakeven movement
- partial close at TP1
- trailing stop after TP1
- opposite signal close
- daily loss guard

## Useful commands

- `autopilot on`
- `autopilot off`
- `manager`
- `manager on`
- `manager off`
- `trades`
- `profit`
- `breakeven gold`
- `close half gold`

## Voice

Voice still does not start automatically. Use:

- `voice`

## Safety

This upgrade does not bypass:

- confidence threshold
- session quota
- Order Punch Shield
- demo-only protection
- spread guard
- MT5 order_check

