# Phase 15.23 — Smart Autopilot Session Guard

This upgrade fixes the issue where Blue showed strong A/A+ setups but did not attempt execution because soft filters were too strict.

## What changed

- Autopilot minimum confidence remains strict: **80%+**.
- A/A+ setups with 80%+ confidence and ML score 75+ are no longer blocked only because of soft advisory warnings.
- Multi-agent disagreement becomes a warning for strong setups instead of an automatic block.
- Portfolio exposure becomes a caution for strong setups; final MT5/order/risk/quota guards still apply.
- Economic calendar stays warning-only when config says warning-only.
- Hard blocks remain active for WAIT signals, low confidence, low ML score, invalid risk, broker rejection, spread, quota, demo-only lock, and Order Punch Shield.

## New session quota

- Maximum **2 Blue auto trades per day**.
- Maximum **1 London session trade**.
- Maximum **1 New York session trade**.
- If London entry is not used, it can roll into New York.

## Voice behavior

Voice does **not** start automatically now.
Use this command when needed:

```text
voice
```

Text commands still work normally.
