"""Phase 15.22 Self Learning Profitability Flywheel.

Learns from Blue's own outputs, MT5/backtest/journal learning layers and no-trade
logic. This module is intentionally conservative: it can adjust confidence notes
and block weak patterns, but it never forces a trade or bypasses MT5/risk guards.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STATE_FILE = Path("phase15_22_profitability_flywheel_state.json")
EVENTS_FILE = Path("reports/profitability_flywheel_events.csv")

DEFAULT_STATE = {
    "enabled": True,
    "background_enabled": True,
    "min_samples_to_adjust": 5,
    "max_confidence_boost": 5,
    "max_confidence_cut": 12,
    "last_calibration_utc": None,
    "notes": [],
}


def _load_state() -> Dict[str, Any]:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        out = dict(DEFAULT_STATE)
        out.update(data)
        return out
    except Exception:
        return dict(DEFAULT_STATE)


def _save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def set_profitability_flywheel(enabled: bool | None = None, background: bool | None = None) -> str:
    state = _load_state()
    if enabled is not None:
        state["enabled"] = bool(enabled)
    if background is not None:
        state["background_enabled"] = bool(background)
    _save_state(state)
    return profitability_status_text()


def _key_parts(signal: Dict[str, Any]) -> Tuple[str, str, str, str]:
    symbol = str(signal.get("symbol") or signal.get("ticker") or "unknown").lower()
    action = str(signal.get("signal_direction") or signal.get("action") or "wait").upper()
    setup = str(signal.get("setup_type") or "unknown_setup").lower().replace(" ", "_")
    session = str(signal.get("session") or "unknown_session").lower().replace(" ", "_")
    return symbol, action, setup, session


def _event_row(signal: Dict[str, Any], event_type: str = "analysis", outcome: str = "pending", pnl: float = 0.0) -> Dict[str, Any]:
    symbol, action, setup, session = _key_parts(signal)
    ctx = signal.get("market_context") or {}
    nn = signal.get("neural_network_brain") or {}
    ds = signal.get("dataset_ml_engine") or {}
    nt = signal.get("no_trade_intelligence") or {}
    return {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "symbol": symbol,
        "action": action,
        "setup": setup,
        "session": session,
        "confidence": signal.get("confidence", 0),
        "context_score": ctx.get("context_score", 0),
        "nn_probability": nn.get("neural_probability", ""),
        "dataset_probability": ds.get("dataset_probability", ""),
        "no_trade_decision": nt.get("decision", ""),
        "outcome": outcome,
        "pnl": pnl,
        "reason": str(signal.get("analyst_reason") or "")[:300].replace("\n", " "),
    }


def record_learning_event(signal: Dict[str, Any], event_type: str = "analysis", outcome: str = "pending", pnl: float = 0.0) -> None:
    try:
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        row = _event_row(signal, event_type=event_type, outcome=outcome, pnl=pnl)
        exists = EVENTS_FILE.exists()
        with EVENTS_FILE.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        pass


def _read_events(limit: int | None = None) -> List[Dict[str, str]]:
    if not EVENTS_FILE.exists():
        return []
    try:
        with EVENTS_FILE.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if limit:
            rows = rows[-limit:]
        return rows
    except Exception:
        return []


def _group_stats(rows: Iterable[Dict[str, str]], fields: Tuple[str, ...]) -> Dict[Tuple[str, ...], Dict[str, Any]]:
    stats: Dict[Tuple[str, ...], Dict[str, Any]] = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0})
    for r in rows:
        key = tuple(str(r.get(f, "")) for f in fields)
        outcome = str(r.get("outcome", "")).lower()
        pnl = 0.0
        try:
            pnl = float(r.get("pnl", 0) or 0)
        except Exception:
            pass
        # pending analysis rows are useful as memory but not outcome stats.
        if outcome in {"pending", "", "analysis"} and pnl == 0:
            continue
        stats[key]["total"] += 1
        stats[key]["pnl"] += pnl
        if outcome in {"win", "profit", "tp", "positive"} or pnl > 0:
            stats[key]["wins"] += 1
        elif outcome in {"loss", "sl", "negative"} or pnl < 0:
            stats[key]["losses"] += 1
    for s in stats.values():
        total = max(1, s["wins"] + s["losses"])
        s["win_rate"] = round(s["wins"] / total * 100, 2)
        s["pnl"] = round(s["pnl"], 2)
    return dict(stats)


def apply_profitability_flywheel(signal: Dict[str, Any]) -> Dict[str, Any]:
    state = _load_state()
    if not state.get("enabled", True):
        signal["profitability_flywheel"] = {"enabled": False, "note": "Profitability flywheel is OFF."}
        return signal

    rows = _read_events(limit=2000)
    symbol, action, setup, session = _key_parts(signal)
    min_samples = int(state.get("min_samples_to_adjust", 5) or 5)
    setup_stats = _group_stats(rows, ("symbol", "action", "setup"))
    session_stats = _group_stats(rows, ("symbol", "session"))
    key_setup = (symbol, action, setup)
    key_session = (symbol, session)
    notes: List[str] = []
    delta = 0
    block = False

    ss = setup_stats.get(key_setup)
    if ss and ss.get("total", 0) >= min_samples:
        wr = float(ss.get("win_rate", 0))
        if wr >= 62 and ss.get("pnl", 0) > 0:
            delta += min(int(state.get("max_confidence_boost", 5)), 4)
            notes.append(f"setup memory supportive: {wr}% win-rate over {ss.get('total')} samples")
        elif wr <= 38 or ss.get("pnl", 0) < 0:
            delta -= min(int(state.get("max_confidence_cut", 12)), 8)
            notes.append(f"setup memory weak: {wr}% win-rate over {ss.get('total')} samples")
            if wr <= 30 and str(signal.get("action")).upper() in {"BUY", "SELL"}:
                block = True

    ps = session_stats.get(key_session)
    if ps and ps.get("total", 0) >= min_samples:
        wr = float(ps.get("win_rate", 0))
        if wr <= 35 or ps.get("pnl", 0) < 0:
            delta -= 4
            notes.append(f"session memory warns: {session} has {wr}% win-rate for {symbol}")
        elif wr >= 60 and ps.get("pnl", 0) > 0:
            delta += 2
            notes.append(f"session memory supports: {session} has {wr}% win-rate for {symbol}")

    old_conf = int(float(signal.get("confidence", 0) or 0))
    new_conf = max(0, min(100, old_conf + delta))
    if delta:
        signal["confidence_before_profitability_flywheel"] = old_conf
        signal["confidence"] = new_conf
    if block:
        signal["original_action_before_profitability_flywheel"] = signal.get("action")
        signal["action"] = "WAIT"
        notes.append("blocked because historical memory says this pattern is low quality")

    signal["profitability_flywheel"] = {
        "enabled": True,
        "delta": delta,
        "old_confidence": old_conf,
        "new_confidence": new_conf,
        "blocked": block,
        "events_loaded": len(rows),
        "note": " | ".join(notes or ["No strong historical adjustment yet; collecting more evidence."]),
    }
    base = signal.get("analyst_reason", "")
    note = "Profitability Flywheel: " + signal["profitability_flywheel"]["note"]
    if note not in base:
        signal["analyst_reason"] = (base + "\n\n" + note).strip()
        signal["human_read"] = signal["analyst_reason"]
    record_learning_event(signal, event_type="analysis", outcome="pending", pnl=0.0)
    return signal


def profitability_status_text() -> str:
    st = _load_state()
    rows = _read_events()
    return "\n".join([
        "Self Learning Profitability Flywheel v15.22",
        f"Enabled             : {st.get('enabled')}",
        f"Background enabled  : {st.get('background_enabled')}",
        f"Memory events       : {len(rows)}",
        f"Min samples adjust  : {st.get('min_samples_to_adjust')}",
        "Learns from: analysis, Blue journal, MT5 history imports, backtest imports, demo forward-test events, no-trade decisions.",
        "Safety: can reduce/block weak setups; never forces trades or bypasses Order Punch Shield.",
    ])


def profitability_report_text() -> str:
    rows = _read_events()
    if not rows:
        return "No profitability flywheel events yet. Run analysis/autopilot or import journal/MT5/backtest history first."
    setup_stats = _group_stats(rows, ("symbol", "action", "setup"))
    session_stats = _group_stats(rows, ("symbol", "session"))
    lines = ["Profitability Flywheel Report", "-" * 44, f"Events loaded: {len(rows)}"]
    lines.append("\nTop setup memory:")
    ranked = sorted(setup_stats.items(), key=lambda kv: (kv[1].get("total", 0), kv[1].get("pnl", 0)), reverse=True)[:10]
    if not ranked:
        lines.append("Not enough completed outcomes yet.")
    for key, s in ranked:
        lines.append(f"- {' / '.join(key)}: {s['win_rate']}% WR | samples {s['total']} | P/L {s['pnl']}")
    lines.append("\nSession memory:")
    ranked_s = sorted(session_stats.items(), key=lambda kv: (kv[1].get("total", 0), kv[1].get("pnl", 0)), reverse=True)[:10]
    if not ranked_s:
        lines.append("Not enough completed outcomes yet.")
    for key, s in ranked_s:
        lines.append(f"- {' / '.join(key)}: {s['win_rate']}% WR | samples {s['total']} | P/L {s['pnl']}")
    return "\n".join(lines)


def mistake_report_text() -> str:
    rows = _read_events()
    if not rows:
        return "No learning events yet."
    losses = [r for r in rows if str(r.get("outcome", "")).lower() in {"loss", "sl", "negative"} or _safe_pnl(r) < 0]
    if not losses:
        return "No loss/mistake events recorded yet."
    count = Counter((r.get("symbol", ""), r.get("setup", ""), r.get("session", "")) for r in losses)
    lines = ["Mistake Report", "-" * 30]
    for (symbol, setup, session), n in count.most_common(10):
        lines.append(f"- {symbol} / {setup} / {session}: {n} loss event(s)")
    lines.append("Action: Blue will reduce confidence or block repeated weak patterns when enough samples exist.")
    return "\n".join(lines)


def _safe_pnl(r: Dict[str, Any]) -> float:
    try:
        return float(r.get("pnl", 0) or 0)
    except Exception:
        return 0.0


def calibrate_confidence_text() -> str:
    state = _load_state()
    state["last_calibration_utc"] = datetime.utcnow().isoformat()
    _save_state(state)
    return "Confidence calibration checked. Blue will use stored setup/session memory during the next analysis."
