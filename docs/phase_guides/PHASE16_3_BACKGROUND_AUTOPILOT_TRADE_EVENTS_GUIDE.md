# Phase 16.3 — Background Autopilot Trade Events

This phase strengthens Phase 16.2 so autopilot does not block the terminal and Blue reacts immediately when a trade is opened.

## What works automatically

- Autopilot scans every 5 minutes in a background thread.
- Terminal stays free so you can type commands while autopilot scans.
- When autopilot punches a trade, Blue immediately prints a clean trade-opened card.
- The trade manager is started/confirmed automatically after the order.
- Blue runs one immediate manager check after the order.
- The always-active trade manager continues to manage BE, partial close, trailing and protection.
- A trade event log is saved to `reports/autopilot_trade_events.jsonl`.

## Safety

This layer does not place extra trades by itself. It only reacts after autopilot order execution succeeds.
Order Punch Shield, session quota, Gold reserved slot, demo lock, risk guard and manager safety remain active.

## Terminal behavior

After a new trade, the terminal shows:

- symbol
- action
- confidence
- grade
- entry
- SL
- TP1 / TP2
- manager status
- useful next commands

You do not need to wait for the full autopilot cycle to finish.
