"""Phase 16.3 Background Trade Event Layer.

Keeps Blue responsive after autopilot punches an order:
- prints an immediate clean trade card
- starts / confirms always-active manager
- runs one immediate manager check
- records a lightweight event log
This layer is intentionally safe: it never sends a new order by itself.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

EVENT_LOG = Path("reports/autopilot_trade_events.jsonl")


def _grade(result: Dict[str, Any]) -> str:
    g = result.get("trade_quality_grades") or {}
    return str(g.get("overall") or g.get("setup") or result.get("setup_grade") or "N/A").upper()


def _safe_write_event(result: Dict[str, Any], exec_msg: str) -> None:
    try:
        EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "symbol": result.get("symbol"),
            "ticker": result.get("ticker"),
            "action": result.get("action"),
            "confidence": result.get("confidence"),
            "grade": _grade(result),
            "entry": result.get("entry"),
            "stop_loss": result.get("stop_loss"),
            "target_1": result.get("target_1"),
            "target_2": result.get("target_2"),
            "exec_message": str(exec_msg)[:1200],
        }
        with EVENT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def format_autopilot_trade_opened_card(result: Dict[str, Any], exec_msg: str) -> str:
    """Immediate card printed as soon as autopilot sees AUTO TRADE DONE."""
    return "\n".join([
        "",
        "╔" + "═" * 70 + "╗",
        "║" + " NEW AUTOPILOT TRADE OPENED ".center(70) + "║",
        "╠" + "═" * 70 + "╣",
        f"║ Symbol      : {str(result.get('symbol', 'UNKNOWN'))[:53]:<53} ║",
        f"║ Action      : {str(result.get('action', '')).upper()[:53]:<53} ║",
        f"║ Confidence  : {str(result.get('confidence', '')) + '%':<53} ║",
        f"║ Grade       : {_grade(result)[:53]:<53} ║",
        f"║ Entry       : {str(result.get('entry', ''))[:53]:<53} ║",
        f"║ Stop Loss   : {str(result.get('stop_loss', ''))[:53]:<53} ║",
        f"║ Target 1    : {str(result.get('target_1', ''))[:53]:<53} ║",
        f"║ Target 2    : {str(result.get('target_2', ''))[:53]:<53} ║",
        "╠" + "═" * 70 + "╣",
        "║ Manager     : ALWAYS ACTIVE — BE / partial / trail will run        ║",
        "║ Terminal    : FREE — type commands anytime, no need to wait         ║",
        "║ Commands    : trades | profit | manager | breakeven <symbol>       ║",
        "╚" + "═" * 70 + "╝",
        "",
    ])


def handle_autopilot_trade_opened(result: Dict[str, Any], exec_msg: str, print_fn=print) -> Dict[str, Any]:
    """Run post-order actions without blocking the autopilot cycle.

    This is called after order_send success. It confirms manager background,
    runs one immediate management scan, and logs the event.
    """
    _safe_write_event(result, exec_msg)
    details = []
    try:
        from .auto_manager import start_auto_manager_background, manage_once
        details.append(start_auto_manager_background())
        details.append("Immediate manager check after entry:")
        details.append(manage_once())
    except Exception as exc:
        details.append(f"Immediate background manager check failed safely: {exc}")
    msg = "\n".join([str(x) for x in details if x])
    try:
        print_fn(msg, flush=True)
    except TypeError:
        print_fn(msg)
    return {"ok": True, "message": msg, "event_log": str(EVENT_LOG)}
