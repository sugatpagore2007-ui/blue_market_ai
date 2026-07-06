# Phase 17 — Clean Architecture Refactor

This phase does not remove old features. It makes the project easier to use and maintain.

## What changed

Before, the project had many top-level folders. Now the root is clean:

```text
blue.py          # main file to run
RUN_BLUE.bat     # Windows launcher
blue_engine/     # all existing Blue code and data
architecture_map/
docs/
storage_area/
```

## Why this is better

- You only run `blue.py`.
- The full system remains modular inside `blue_engine/`.
- Old imports still work because `blue.py` runs the original engine from inside the engine folder.
- Future upgrades can be added without making the root project messy.

## Preserved features

- Autopilot
- 5-minute scan
- Clean background terminal
- Immediate order-punched card
- Auto trade manager after entry
- Gold reserved quota
- CME institutional brain
- Phase 16.2 evolution engine
- Self-healing doctor
- Order Punch Shield
- Natural intent brain
- Voice only starts on command: `voice`

## How to run

```bash
python blue.py
```

Do not run internal files unless debugging.
