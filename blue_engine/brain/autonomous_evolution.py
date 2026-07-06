"""Phase 16.2 — Autonomous Evolution Engine.

Automatic advisory/evolution layer for Blue:
- Monday weekly report generation
- autopilot 5-minute cycle support
- verified-learning promotion pipeline foundation
- market DNA / confidence calibration / source trust state
- post-order reflection hook

Safety rule: this module never sends orders and never bypasses Order Punch Shield.
It only adds context, ranking hints, report files, and small advisory confidence tags.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

STATE_FILE = Path("phase16_2_autonomous_evolution_state.json")
REPORT_DIR = Path("reports/evolution")
MEMORY_DIR = Path("brain_memory/evolution")
WEEKLY_REPORT_FILE = REPORT_DIR / "latest_monday_evolution_report.md"

DEFAULT_INTERVAL_SECONDS = 60 * 15

_thread: Optional[threading.Thread] = None
_stop = threading.Event()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _state() -> Dict[str, Any]:
    default = {
        "enabled": True,
        "background": True,
        "running": False,
        "interval_seconds": DEFAULT_INTERVAL_SECONDS,
        "last_pulse": None,
        "last_message": "Autonomous Evolution Engine has not run yet.",
        "last_monday_report_date": None,
        "autopilot_scan_seconds": 300,
        "source_trust": {
            "mt5_history": 95,
            "blue_journal": 90,
            "cme_group": 85,
            "backtest": 80,
            "economic_calendar": 75,
            "internet": 35,
            "video_notes": 30,
        },
        "promotion_pipeline": {
            "sandbox": [],
            "historical_validation": [],
            "demo_validation": [],
            "production_candidates": [],
        },
        "market_dna": {},
        "confidence_calibration": {},
        "autopilot": {
            "cycle_count": 0,
            "last_cycle_at": None,
            "last_best_gold": None,
            "last_best_other": None,
        },
    }
    data = _read_json(STATE_FILE, {})
    if isinstance(data, dict):
        # shallow merge with defaults
        for k, v in default.items():
            data.setdefault(k, v)
        return data
    return default


def _save(**updates: Any) -> Dict[str, Any]:
    st = _state()
    st.update(updates)
    st["updated_at"] = _now()
    _write_json(STATE_FILE, st)
    return st


def _symbol_key(signal: Dict[str, Any]) -> str:
    raw = str(signal.get("symbol") or signal.get("ticker") or "UNKNOWN").upper()
    raw = raw.replace("=X", "").replace("-USD", "USD").replace("/", "")
    if "GOLD" in raw or "XAU" in raw or "GC" == raw:
        return "XAUUSD"
    if "SILVER" in raw or "XAG" in raw:
        return "XAGUSD"
    if "BTC" in raw:
        return "BTCUSD"
    if "ETH" in raw:
        return "ETHUSD"
    if "OIL" in raw or raw == "CL":
        return "USOIL"
    if "USTEC" in raw or "NASDAQ" in raw or raw == "NQ":
        return "USTEC"
    for s in ["EURUSD", "GBPUSD", "USDJPY"]:
        if s in raw:
            return s
    return raw[:20]


def _grade(signal: Dict[str, Any]) -> str:
    g = signal.get("trade_quality_grades") or {}
    return str(g.get("overall") or g.get("setup") or signal.get("setup_grade") or "").upper().strip()


def _is_gold(signal: Dict[str, Any]) -> bool:
    return _symbol_key(signal) == "XAUUSD"


def _score_candidate(signal: Dict[str, Any]) -> float:
    conf = float(signal.get("confidence") or 0)
    grade_bonus = {"A+": 8, "A": 5, "B+": 2}.get(_grade(signal), 0)
    cme = signal.get("cme_group_brain") or {}
    cme_bonus = 2 if str(cme.get("confirmation")) in {"supports_buy", "supports_sell"} else 0
    if str(cme.get("confirmation")) == "divergence_warning":
        cme_bonus = -3
    fly = signal.get("profitability_flywheel") or {}
    fly_bonus = float(fly.get("confidence_delta") or 0)
    nt = signal.get("no_trade_intelligence") or {}
    block_penalty = -20 if nt and not nt.get("allow_trade", True) else 0
    return round(conf + grade_bonus + cme_bonus + fly_bonus + block_penalty, 2)


def _summarize_states() -> Dict[str, Any]:
    files = {
        "quota": Path("phase15_22_session_trade_quota_state.json"),
        "profitability": Path("phase15_22_profitability_flywheel_state.json"),
        "cognitive": Path("phase16_cognitive_architecture_state.json"),
        "cme": Path("phase16_1_cme_group_brain_state.json"),
        "autopilot": Path("blue_autopilot_state.json"),
        "self_healing": Path("phase15_24_self_healing_state.json"),
        "neural": Path("phase15_19_neural_network_state.json"),
    }
    return {k: _read_json(v, {}) for k, v in files.items()}


def generate_monday_report(force: bool = False) -> Dict[str, Any]:
    st = _state()
    today = _today()
    weekday = datetime.now().weekday()  # Monday=0
    if not force and weekday != 0:
        return {"ok": True, "generated": False, "message": "Monday report not due today."}
    if not force and st.get("last_monday_report_date") == today:
        return {"ok": True, "generated": False, "message": "Monday report already generated today."}

    states = _summarize_states()
    quota = states.get("quota", {})
    pfit = states.get("profitability", {})
    cme = states.get("cme", {})
    cognitive = states.get("cognitive", {})
    lines = [
        "# Blue Weekly Evolution Report",
        "",
        f"Generated: {_now()}",
        "",
        "## What Blue reviewed",
        "- Autopilot state",
        "- Gold/Other reserved quota state",
        "- Profitability flywheel state",
        "- Cognitive architecture state",
        "- CME institutional context state",
        "- Neural/self-healing state",
        "",
        "## Current trading policy",
        "- Autopilot scan interval: 5 minutes",
        "- Daily auto trades: max 2",
        "- Gold slot: 1 trade only, A+ or 100% confidence required",
        "- Other-pair slot: 1 trade only",
        "- If London gives no trade, New York can still use the same two slots only",
        "- Order Punch Shield and self-healing remain active",
        "",
        "## Snapshot",
        f"- Quota: `{str(quota)[:900]}`",
        f"- Profitability flywheel: `{str(pfit)[:900]}`",
        f"- CME: `{str(cme)[:700]}`",
        f"- Cognitive: `{str(cognitive)[:700]}`",
        "",
        "## Evolution decisions",
        "- Keep learning from all sources, but promote only verified knowledge.",
        "- Prioritize MT5 history, Blue journal, CME context, and demo forward test over internet/video notes.",
        "- Continue ranking Gold separately from other instruments because Gold has its own reserved slot.",
        "- If repeated order rejections appear, run Order Doctor and Self-Healing Doctor automatically/visibly.",
        "",
        "## Next focus",
        "- Improve setup quality, not trade quantity.",
        "- Track which sessions and instruments actually convert confidence into profit.",
        "- Reduce confidence for setups that underperform in live/demo results.",
    ]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    WEEKLY_REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    archive = REPORT_DIR / f"monday_evolution_report_{today}.md"
    archive.write_text("\n".join(lines), encoding="utf-8")
    _save(last_monday_report_date=today, last_message=f"Monday evolution report generated: {WEEKLY_REPORT_FILE}")
    return {"ok": True, "generated": True, "message": f"Monday evolution report generated: {WEEKLY_REPORT_FILE}", "file": str(WEEKLY_REPORT_FILE)}


def apply_autonomous_evolution(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Attach advisory evolution context to every signal, including autopilot scans."""
    try:
        st = _state()
        sym = _symbol_key(signal)
        dna = st.setdefault("market_dna", {}).setdefault(sym, {"observations": 0, "notes": []})
        score = _score_candidate(signal)
        notes = list(dna.get("notes") or [])
        if _is_gold(signal) and "reserved_gold_slot" not in notes:
            notes.append("reserved_gold_slot")
        if score >= 90 and "high_quality_candidate" not in notes:
            notes.append("high_quality_candidate")
        dna["observations"] = int(dna.get("observations", 0) or 0) + 1
        dna["last_seen"] = _now()
        dna["last_score"] = score
        dna["notes"] = notes[-10:]
        signal["autonomous_evolution"] = {
            "active": True,
            "version": "16.2",
            "candidate_score": score,
            "market_dna_notes": notes[-5:],
            "source_trust": st.get("source_trust", {}),
            "promotion_rule": "Learn everything, trust nothing, test everything, promote only verified knowledge.",
            "note": "Phase 16.2 advisory layer active for autopilot and manual analysis. It never sends orders directly.",
        }
        _write_json(MEMORY_DIR / "market_dna.json", st.get("market_dna", {}))
        _save(market_dna=st.get("market_dna", {}), last_message=f"Signal reviewed by Autonomous Evolution Engine: {sym} score {score}")
    except Exception as exc:
        signal["autonomous_evolution"] = {"active": False, "error": str(exc), "note": "Phase 16.2 skipped safely."}
    return signal


def autopilot_cycle_pulse(cycle: int, analyzed: Optional[List[Dict[str, Any]]] = None, print_fn: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Called by autopilot each cycle. Keeps evolution active inside autopilot."""
    analyzed = analyzed or []
    gold = [x for x in analyzed if _is_gold(x)]
    other = [x for x in analyzed if not _is_gold(x)]
    best_gold = max(gold, key=_score_candidate, default=None)
    best_other = max(other, key=_score_candidate, default=None)
    msg_parts = [f"Phase 16.2 autopilot evolution pulse #{cycle}: 5-minute scan brain active."]
    if best_gold:
        msg_parts.append(f"Best Gold slot candidate: {_symbol_key(best_gold)} score {_score_candidate(best_gold)} conf {best_gold.get('confidence')}% grade {_grade(best_gold) or 'N/A'}")
    if best_other:
        msg_parts.append(f"Best Other slot candidate: {_symbol_key(best_other)} score {_score_candidate(best_other)} conf {best_other.get('confidence')}% grade {_grade(best_other) or 'N/A'}")
    auto_state = _state().get("autopilot", {})
    auto_state.update({
        "cycle_count": cycle,
        "last_cycle_at": _now(),
        "last_best_gold": _symbol_key(best_gold) if best_gold else None,
        "last_best_other": _symbol_key(best_other) if best_other else None,
    })
    _save(autopilot=auto_state, last_pulse=_now(), last_message=" | ".join(msg_parts))
    try:
        rep = generate_monday_report(force=False)
        if rep.get("generated"):
            msg_parts.append(rep.get("message", "Monday report generated."))
    except Exception:
        pass
    msg = "\n".join(msg_parts)
    if print_fn:
        print_fn(msg)
    return {"ok": True, "message": msg}


def on_autopilot_order_punched(signal: Dict[str, Any], execution_message: str = "") -> Dict[str, Any]:
    """Post-order hook: records immediate reflection seed and keeps manager/evolution tied to entries."""
    sym = _symbol_key(signal)
    data = {
        "time": _now(),
        "symbol": sym,
        "action": signal.get("action"),
        "confidence": signal.get("confidence"),
        "grade": _grade(signal),
        "entry": signal.get("entry"),
        "stop_loss": signal.get("stop_loss"),
        "target_1": signal.get("target_1"),
        "target_2": signal.get("target_2"),
        "candidate_score": _score_candidate(signal),
        "execution_message": str(execution_message)[:1200],
        "reflection_seed": "Review this trade after close: entry timing, session quality, CME agreement, slippage, and management result.",
    }
    log_file = MEMORY_DIR / "autopilot_order_reflections.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=str) + "\n")
    _save(last_message=f"Autopilot order reflection seed saved for {sym}.")
    return {"ok": True, "message": f"Phase 16.2 saved post-order reflection seed for {sym}."}


def run_evolution_pulse(force_monday_report: bool = False) -> Dict[str, Any]:
    rep = generate_monday_report(force=force_monday_report)
    _save(last_pulse=_now(), last_message=rep.get("message", "Evolution pulse complete."))
    return {"ok": True, "message": "Autonomous Evolution pulse complete. " + rep.get("message", ""), "monday_report": rep}


def evolution_status_text() -> str:
    st = _state()
    return "\n".join([
        "Phase 16.2 Autonomous Evolution Engine",
        f"Enabled              : {st.get('enabled')}",
        f"Background           : {st.get('background')}",
        f"Running              : {st.get('running')}",
        f"Autopilot scan       : {st.get('autopilot_scan_seconds')} seconds / 5 minutes",
        f"Last pulse           : {st.get('last_pulse')}",
        f"Last Monday report   : {st.get('last_monday_report_date')}",
        f"Latest report file   : {WEEKLY_REPORT_FILE}",
        "Daily trade rule     : 2/day = 1 Gold slot + 1 other-pair slot across London/NY",
        "Gold slot            : A+ or 100% confidence required",
        "Safety               : advisory only; autopilot/order shield still decides execution.",
        f"Last message         : {st.get('last_message')}",
    ])


def _loop(print_fn: Optional[Callable[[str], None]] = None) -> None:
    _save(running=True, started_at=_now(), last_message="Autonomous Evolution background worker started.")
    while not _stop.wait(5):
        try:
            st = _state()
            last = st.get("last_pulse")
            due = True
            if last:
                try:
                    then = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                    due = (datetime.now(timezone.utc) - then).total_seconds() >= int(st.get("interval_seconds", DEFAULT_INTERVAL_SECONDS))
                except Exception:
                    due = True
            if due:
                res = run_evolution_pulse(force_monday_report=False)
                if print_fn and res.get("monday_report", {}).get("generated"):
                    print_fn("Evolution Engine: " + str(res.get("message")))
        except Exception as exc:
            _save(last_error=str(exc), last_message="Evolution pulse failed safely: " + str(exc))
    _save(running=False, stopped_at=_now(), last_message="Autonomous Evolution background worker stopped.")


def start_autonomous_evolution_service(print_fn: Optional[Callable[[str], None]] = None, force: bool = False) -> Dict[str, Any]:
    global _thread
    st = _state()
    if not st.get("enabled", True) or not st.get("background", True):
        return {"ok": True, "started": False, "message": "Autonomous Evolution Engine is OFF."}
    if _thread and _thread.is_alive() and not force:
        return {"ok": True, "started": False, "message": "Autonomous Evolution Engine already running."}
    _stop.clear()
    _thread = threading.Thread(target=_loop, kwargs={"print_fn": print_fn}, daemon=True, name="BlueAutonomousEvolution")
    _thread.start()
    # Generate Monday report immediately if due, but do not block startup.
    try:
        generate_monday_report(force=False)
    except Exception:
        pass
    return {"ok": True, "started": True, "message": "Autonomous Evolution Engine background worker started."}


def stop_autonomous_evolution_service() -> Dict[str, Any]:
    _stop.set()
    _save(running=False, last_message="Autonomous Evolution stop requested.")
    return {"ok": True, "message": "Autonomous Evolution Engine stop requested."}
