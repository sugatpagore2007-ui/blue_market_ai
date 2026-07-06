# Phase 15.27 — Gold Reserved Quota

This phase changes the daily autopilot quota rule.

## Final rule

- Maximum auto entries per day: **2**
- Trade only during London or New York session
- One slot is reserved for **Gold / XAUUSD only**
- One slot is reserved for **all other pairs/instruments**
- If Blue does not trade in London, New York can still take only the same 2 slots:
  - 1 Gold slot
  - 1 other-pair slot

## Gold quality rule

Gold/XAUUSD can use the reserved Gold slot only if:

- setup grade is **A+**, or
- confidence is **100%**

If Gold is only A or below 100% without A+, Blue blocks the Gold slot and waits.

## Other-pair slot

The second daily slot can be used by other major/default instruments such as:

- EURUSD
- GBPUSD
- USDJPY
- USTEC
- BTCUSD
- ETHUSD
- XAGUSD
- USOIL

Gold cannot use the other-pair slot.

## Example

London session:

- No valid Gold A+ setup
- No valid other setup

New York session:

- Gold A+ appears → Blue can take Gold trade
- EURUSD A setup appears → Blue can take other-pair trade
- After that, daily limit is reached

## Safety

This quota does not bypass:

- confidence minimum
- A+ / smart autopilot filters
- daily loss guard
- Order Punch Shield
- MT5 broker checks
- auto trade manager
