# Phase 15.20 — Human Trader Natural Brain

This upgrade was added **without changing the whole codebase**.
It extends the existing Human Trader Brain and Neural + Order Punch Shield layers.

## What is new

Blue now thinks more like a natural human trader:

1. **Market Story Brain**  
   Blue explains the market in natural language instead of only saying BUY / SELL / WAIT.

2. **Scenario Planning**  
   Blue gives Plan A / Plan B / Plan C.

3. **Trade Invalidation**  
   Blue says what level invalidates the current idea.

4. **Patience Filter**  
   Blue reminds you not to chase price and to wait for the level.

5. **Natural Report Layer**  
   Works on top of the current analysis; it does not bypass risk rules or order safety.

## New commands added (old commands unchanged)

- `human brain`
- `human report`
- `safe trader mode`
- `aggressive trader mode`
- `market story gold`
- `scenario gold`
- `plan gold`
- `trade invalidation gold`
- `why wait`
- `should we take this trade`

These also work in voice mode through the command parser.

## Safety

This layer is **advisory only**.
It does **not** directly punch orders.
Orders still depend on:

- SMC/ICT + existing logic
- ML / Neural confirmation
- No-Trade intelligence
- MT5 broker checks
- Order Punch Shield
- risk / autopilot filters

