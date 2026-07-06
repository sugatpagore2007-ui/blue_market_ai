# Phase 15.22 — Self Learning Profitability Flywheel + Session Trade Quota

This upgrade is added on top of Phase 15.21. Old commands are kept.

## Self Learning Profitability Flywheel

Blue now builds a conservative learning loop:

Observe → Store → Label → Test → Learn → Confirm → Trade small → Review → Improve

It stores analysis/no-trade memory in:

- `reports/profitability_flywheel_events.csv`
- `phase15_22_profitability_flywheel_state.json`

It can use setup/session memory to slightly increase confidence for historically strong patterns and reduce/block historically weak repeated patterns.

Safety rule: the flywheel can **reduce or block** weak setups, but it never forces trades and never bypasses the Order Punch Shield.

## New commands

- `self learn`
- `self learn on`
- `self learn off`
- `self report`
- `profitability report`
- `mistake report`
- `calibrate confidence`
- `session quota`
- `trade quota`
- `daily quota`

## Session Trade Quota

Requested rule:

- Maximum **4 automatic trades per day**
- Maximum **1 London session trade**
- Maximum **1 New York session trade**
- If London trades are not used, unused London capacity can roll into New York

Example:

- London used 0/2 → New York can take up to 4 total if A+ setups appear
- London used 1/2 → New York can take up to 3 total
- London used 2/2 → New York can take up to 2

Auto entries outside London/New York are blocked by the session quota.

State file:

- `phase15_22_session_trade_quota_state.json`

## Order Safety

Execution still depends on:

- SMC/ICT signal
- ML / Neural confirmation
- Profitability Flywheel memory
- No-trade intelligence
- Daily/session quota
- MT5 connection
- Demo account guard
- Spread/risk checks
- Order Punch Shield

