# Blue Forex AI — Systematic Project Structure

This ZIP keeps one production project folder and organizes phase history inside `docs/phases/`.
Runtime state JSON files remain in the root for backward compatibility, and are also copied into `storage/state/` for easy browsing.

## Main runtime
- `main.py` — start Blue
- `config.py` — main configuration
- `requirements.txt` — base packages
- `RUN_BLUE_FOREX_AI.bat` / `RUN_BLUE_FULL_AUTO.bat` — Windows launch helpers

## Core trading modules
- `analysis/` — market signal analysis, SMC/ICT, indicators
- `intelligence/` — ML, human trader brain, no-trade logic, neural/evolution layers
- `mt5_bridge/` — MT5 execution, autopilot, order shield, manager hooks
- `trade_management/` — breakeven, partial close, trailing, management plans
- `risk/` — risk and lot sizing
- `scanner/` — market scanner and opportunity selection

## Learning and memory
- `learning/` — self-learning, history import, backtest import, neural learning hooks
- `knowledge/` — internet/video/strategy learning
- `institutional/` — CME Group/institutional context brain
- `memory/` and `brain_memory/` — memory stores and preferences
- `storage/` — database and organized state copies
- `datasets/` and `models/` — ML data and model files

## Interfaces
- `voice/` — voice mode, background listener, speaker
- `vision/` — screenshot/OCR/chart vision
- `dashboard/` — dashboard app
- `ui/` — terminal/orb UI helpers
- `utils/` — command parsing and support utilities

## Documentation
- `docs/phases/` — all phase guides in one folder
- `docs/commands/` — friendly command guide
- `docs/architecture/` — structure map
- `docs/summaries/` — final upgrade summaries
