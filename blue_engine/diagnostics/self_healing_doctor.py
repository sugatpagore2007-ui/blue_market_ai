"""Phase 15.24 Self-Healing Doctor.

Safe auto-diagnosis layer for Blue. It fixes only safe local issues
(missing folders/state files). Risky problems like MT5 closed, broker reject,
missing package, or order_send retcode are shown clearly in terminal.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STATE_FILE = Path("phase15_24_self_healing_state.json")
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "blue_self_healing.log"
REQUIRED_DIRS = [
    "logs", "reports", "reports/auto_learn", "datasets", "models", "storage",
    "docs", "docs/phase_guides", "knowledge", "memory",
]
OPTIONAL_PACKAGES = {
    "MetaTrader5": "MT5 execution needs MetaTrader5. Install with: pip install MetaTrader5",
    "pandas": "Data/report modules need pandas. Install with: pip install pandas",
    "numpy": "ML/neural modules need numpy. Install with: pip install numpy",
    "sklearn": "ML models need scikit-learn. Install with: pip install scikit-learn",
    "joblib": "Model save/load needs joblib. Install with: pip install joblib",
    "requests": "Internet learning needs requests. Install with: pip install requests",
}
STATE_DEFAULTS = {
    "enabled": True,
    "auto_fix_safe_files": True,
    "last_startup_check": "",
    "last_issue": "",
    "last_fix": "",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> Dict[str, Any]:
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(STATE_DEFAULTS)
                merged.update(data)
                return merged
    except Exception:
        pass
    return dict(STATE_DEFAULTS)


def _save_state(data: Dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def log_event(kind: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"time": _now(), "kind": kind, "message": message, "details": details or {}}
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _status_line(ok: bool, label: str, message: str) -> str:
    icon = "OK " if ok else "FIX" if message.lower().startswith("created") else "WARN"
    return f"{icon:<4} {label:<24} {message}"


def run_startup_self_heal(verbose: bool = False) -> Dict[str, Any]:
    state = _load_state()
    if not state.get("enabled", True):
        return {"ok": True, "message": "Self-Healing Doctor is OFF.", "fixed": [], "warnings": []}

    fixed: List[str] = []
    warnings: List[str] = []
    lines: List[str] = ["SELF-HEALING DOCTOR", "-" * 72]

    # Safe local repair: folders.
    for d in REQUIRED_DIRS:
        p = Path(d)
        if not p.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
                fixed.append(f"Created folder: {d}")
                lines.append(_status_line(False, d, "Created missing folder"))
            except Exception as exc:
                warnings.append(f"Could not create {d}: {exc}")
                lines.append(_status_line(False, d, f"Could not create: {exc}"))
        else:
            lines.append(_status_line(True, d, "ready"))

    # Safe state file repair.
    if not STATE_FILE.exists():
        _save_state(state)
        fixed.append(f"Created state file: {STATE_FILE}")

    # Package check: warn only, never auto-install.
    pkg_warnings = []
    for pkg, help_text in OPTIONAL_PACKAGES.items():
        try:
            importlib.import_module(pkg)
            lines.append(_status_line(True, f"package:{pkg}", "installed"))
        except Exception:
            pkg_warnings.append(help_text)
            lines.append(_status_line(False, f"package:{pkg}", "missing - install if this feature is needed"))
    warnings.extend(pkg_warnings)

    state["last_startup_check"] = _now()
    state["last_fix"] = "; ".join(fixed[-5:])
    state["last_issue"] = "; ".join(warnings[:3])
    _save_state(state)

    ok = len([w for w in warnings if "MetaTrader5" in w or "pandas" in w or "numpy" in w]) == 0
    msg = "Startup self-check complete. " + (f"Fixed {len(fixed)} safe issue(s)." if fixed else "No safe repair needed.")
    log_event("startup_check", msg, {"fixed": fixed, "warnings": warnings})
    return {"ok": ok, "message": msg, "fixed": fixed, "warnings": warnings, "text": "\n".join(lines)}


def explain_exception(exc: BaseException, where: str = "runtime") -> str:
    etype = type(exc).__name__
    msg = str(exc)
    tb = traceback.format_exc(limit=4)
    log_event("exception", f"{where}: {etype}: {msg}", {"traceback": tb})
    suggestions = []
    low = msg.lower()
    if "metatrader5" in low or "mt5" in low:
        suggestions.append("MT5 issue: keep MT5 open, logged in, Algo Trading ON, then type: connect mt5")
        suggestions.append("Run: order doctor gold")
    if "no module named" in low:
        suggestions.append("Missing package: install requirements again with: pip install -r requirements.txt")
    if "permission" in low:
        suggestions.append("Permission issue: close files/Excel/MT5 popup using the file, then run VS Code as normal user/admin if needed.")
    if "symbol" in low:
        suggestions.append("Symbol issue: type broker, then show mt5 symbols gold, or use auto broker.")
    if not suggestions:
        suggestions.append("Type: blue doctor")
        suggestions.append("If order issue: type order doctor gold")
    return "\n".join([
        "",
        "=" * 72,
        "BLUE SELF-HEALING DOCTOR",
        "=" * 72,
        f"Problem area : {where}",
        f"Error type   : {etype}",
        f"Error message: {msg}",
        "",
        "What Blue did:",
        "- Logged the error in logs/blue_self_healing.log",
        "- Kept terminal alive where possible",
        "- Did not hide the failure",
        "",
        "Try this:",
        *[f"- {s}" for s in suggestions],
        "=" * 72,
    ])


def diagnose_order_message(message: str) -> str:
    text = str(message or "")
    low = text.lower()
    tips = []
    if "market is closed" in low or "trade disabled" in low:
        tips.append("Market/broker trading may be closed. Wait for London/NY active session.")
    if "algo" in low or "disabled" in low:
        tips.append("Enable Algo Trading in MT5 and allow automated trading in terminal options.")
    if "spread too high" in low:
        tips.append("Spread guard is protecting you. Wait for lower spread or adjust symbol-specific spread limits only after testing.")
    if "confidence" in low:
        tips.append("Signal did not meet confidence threshold. Blue should wait, not force trade.")
    if "session quota" in low or "daily auto trade limit" in low:
        tips.append("Daily/session quota is doing its job. Type: session quota")
    if "could not select" in low or "missing symbol" in low:
        tips.append("Symbol mapping issue. Type: broker, then order doctor gold / show mt5 symbols gold.")
    if "order_check" in low or "retcode" in low or "failed" in low:
        tips.append("MT5 rejected the order request. Blue prints retcode/last_error; run order doctor for the same symbol.")
    if not tips:
        tips.append("No exact automatic fix found. Type: blue doctor and order doctor gold.")
    return "\n".join(["SELF-HEALING ORDER NOTE:"] + [f"- {t}" for t in tips])


def blue_doctor_text() -> str:
    res = run_startup_self_heal(verbose=False)
    text = res.get("text", "")
    extra = ["", "QUICK COMMANDS", "-" * 72,
             "order doctor gold       -> diagnose execution mechanics",
             "connect mt5             -> connect/check MT5 terminal",
             "session quota           -> show London/NY daily quota",
             "auto status             -> show auto execution guards",
             "self heal on/off        -> enable/disable this doctor"]
    return text + "\n" + "\n".join(extra)


def set_self_healing(enabled: bool) -> str:
    state = _load_state()
    state["enabled"] = bool(enabled)
    _save_state(state)
    return f"Self-Healing Doctor is now {'ON' if enabled else 'OFF'}."
