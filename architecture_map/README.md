# Blue Architecture Map

The actual working code is kept inside `blue_engine/` to avoid breaking imports.
Conceptually, Blue is organized like this:

```text
brain/        = intelligence, learning, neural, memory, CME, evolution
trading/      = analysis, scanner, MT5 bridge, risk, trade management, autopilot
interface/    = terminal, voice, dashboard, UI, command parser
storage/      = datasets, models, reports, journals, logs, databases
system/       = config, diagnostics, self-healing, startup
```

Phase 17 keeps compatibility first. Later, files can be gradually migrated into these folders.
