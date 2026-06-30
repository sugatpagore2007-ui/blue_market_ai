# Phase 15.21 — Natural Intent Brain + Clean Terminal

This upgrade is additive. It keeps all old fixed commands and adds natural command understanding.

## What changed

### 1. Natural Intent Brain
Blue no longer depends only on coded commands. It can understand normal phrases and route them to safe internal commands.

Examples:

- `what is gold doing today` → `check gold`
- `is gold safe to enter or wait` → `check gold` + `why wait`
- `protect my gold trade` → `breakeven gold`
- `why gold not executing order` → `order doctor gold`
- `find best trade` → `strongest`
- `scan all pairs` → `scanner`
- `show my current positions` → `open positions`
- `train your brain` → ready ML training
- `what is the plan for gold` → `scenario gold`
- `when is gold idea wrong` → `trade invalidation gold`

### 2. Old commands still work
All previous commands remain unchanged:

- `gold`
- `eurusd`
- `btc`
- `best`
- `scan`
- `why`
- `autopilot on`
- `order doctor gold`
- `neural report`
- `human brain`
- `market story gold`
- `scenario gold`

### 3. Clean terminal output
Signal output is now printed as one clean card with these sections:

- Action / confidence
- Entry / SL / TP
- Lot size
- Trade reason
- Market story
- Plan A / Plan B / Plan C
- Invalidation
- Brains status
- Patience filter

The detailed data still exists internally and is still saved to journal/signals. The terminal just stays readable.

### 4. Safety
Natural language is routed through the same safe command system.
It does not bypass:

- risk filter
- no-trade brain
- neural/ML confirmation
- MT5 checks
- Order Punch Shield
- demo-only execution default

Manual buy/sell through voice remains protected.

