# Phase 15.26 — London-to-New-York Rollover Quota

This phase updates the Phase 15.25 background trade manager rules.

## Final daily rule

Blue can punch **maximum 2 auto trades per day**.

## London session

- London can take **maximum 1 trade**.
- If London takes 1 trade, London is finished for the day.

## New York session

- If London already traded: New York can take **maximum 1 trade**.
- If London did not trade: New York can take **up to 2 trades**.

## Examples

### Example 1

London takes 1 trade.
New York can take 1 trade.
Total = 2 trades.

### Example 2

London takes 0 trades.
New York can take 2 trades.
Total = 2 trades.

## Safety kept

This quota does not bypass:

- Order Punch Shield
- demo-only protection
- confidence minimum 80%
- daily loss guard
- spread guard
- MT5 order checks
- auto manager

Voice auto-start is still OFF. Voice starts only by command: `voice`.

## Command

Use:

```text
session quota
```

to see current London/NY usage.
