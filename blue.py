"""Blue Market AI - Single Entry Launcher (Phase 17)

Run this file only:
    python blue.py

The full Blue engine is inside ./blue_engine so the root project stays clean.
This launcher keeps backward compatibility by running the original main.py from
inside the engine folder.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "blue_engine"
MAIN_FILE = ENGINE / "main.py"


def main() -> None:
    if not MAIN_FILE.exists():
        print("Blue engine main.py not found.")
        print(f"Expected: {MAIN_FILE}")
        return
    os.chdir(str(ENGINE))
    sys.path.insert(0, str(ENGINE))
    print("=" * 64)
    print("BLUE MARKET AI — PHASE 17 CLEAN ARCHITECTURE")
    print("Run file: blue.py")
    print("Engine   : blue_engine/")
    print("Voice    : OFF until command 'voice'")
    print("Terminal : clean background autopilot mode")
    print("=" * 64)
    runpy.run_path(str(MAIN_FILE), run_name="__main__")


if __name__ == "__main__":
    main()
