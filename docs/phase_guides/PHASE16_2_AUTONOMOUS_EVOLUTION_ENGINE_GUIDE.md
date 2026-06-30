# Phase 16.2 — Autonomous Evolution Engine

This phase works automatically on top of Phase 16.1 and also works inside autopilot.

## What it adds

- Monday weekly evolution report
- 5-minute autopilot scan cycle
- Autopilot evolution pulse on every scan
- Opportunity ranking memory for Gold slot and Other-pair slot
- Verified-learning promotion pipeline foundation
- Market DNA memory
- Confidence calibration foundation
- Source trust scoring
- Post-order reflection seed after autopilot punches a trade

## Autopilot rule

Autopilot scans every 5 minutes.

Trade quota remains:

- Max trades per day: 2
- Gold/XAUUSD slot: 1 trade only
- Other-pair slot: 1 trade only
- Gold slot requires A+ setup or 100% confidence
- If London has no trade, New York can still take only the same two slots: one Gold + one other-pair trade

## After order punch

When autopilot punches an order:

1. Blue immediately shows the trade card.
2. Blue saves a Phase 16.2 reflection seed.
3. Auto manager checks immediately.
4. Auto manager stays active in background.

## Monday report

Every Monday, Blue automatically creates:

`reports/evolution/latest_monday_evolution_report.md`

It reviews:

- quota state
- autopilot state
- profitability flywheel
- CME context
- cognitive architecture
- neural/self-healing state

## Safety

Phase 16.2 is advisory only.
It does not send orders directly.
Order execution still goes through:

- signal engine
- Gold/Other quota
- confidence threshold
- Order Punch Shield
- MT5 broker checks
- demo-only protection
- auto manager

## Optional commands

These commands are optional. The system works automatically.

- `evolution status`
- `evolution now`
- `monday report`
- `weekly evolution report`
