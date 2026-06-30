"""Phase 16 — Blue Cognitive Architecture Auto Brain.

Additive layer. It does not replace existing folders or old commands.
It runs automatically in background and does safe, verified learning:
- world model snapshot
- market DNA memory
- experience replay notes
- confidence calibration hints
- knowledge verification queue
- opportunity ranking hints

Safety: this module never sends/modifies/closes orders. It only writes memory and
advisory scores used by the normal risk/autopilot/order shield pipeline.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

STATE_FILE = Path("phase16_cognitive_architecture_state.json")
MEMORY_DIR = Path("brain_memory")
WORLD_MODEL_FILE = MEMORY_DIR / "world_model.json"
MARKET_DNA_FILE = MEMORY_DIR / "market_dna.json"
EXPERIENCE_REPLAY_FILE = MEMORY_DIR / "experience_replay.json"
VERIFICATION_QUEUE_FILE = MEMORY_DIR / "knowledge_verification_queue.json"
COGNITIVE_INTERVAL_SECONDS = int(os.environ.get("BLUE_COGNITIVE_INTERVAL_SECONDS", "900"))

_MAJOR_SYMBOLS = ["XAUUSD", "XAGUSD", "ETHUSD", "BTCUSD", "USOIL", "USDJPY", "EURUSD", "USTEC", "GBPUSD"]
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None
_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _load_state() -> Dict[str, Any]:
    return _read_json(STATE_FILE, {
        "enabled": True,
        "running": False,
        "started_at": None,
        "last_run": None,
        "loop_count": 0,
        "last_message": "Cognitive Architecture has not run yet.",
        "last_error": None,
    })


def _save_state(**updates: Any) -> Dict[str, Any]:
    st = _load_state()
    st.update(updates)
    st["updated_at"] = _now()
    _write_json(STATE_FILE, st)
    return st


def _safe_symbol(signal: Dict[str, Any]) -> str:
    return str(signal.get("symbol") or signal.get("broker_chart_symbol") or signal.get("ticker") or "UNKNOWN").upper()


def _setup_key(signal: Dict[str, Any]) -> str:
    return str(signal.get("setup_type") or signal.get("regime") or "unknown_setup").lower().replace(" ", "_")[:80]


def _update_market_dna_from_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    symbol = _safe_symbol(signal)
    dna = _read_json(MARKET_DNA_FILE, {})
    row = dna.get(symbol, {
        "symbol": symbol,
        "seen": 0,
        "best_sessions": {},
        "setup_counts": {},
        "confidence_sum": 0.0,
        "last_seen": None,
        "personality_notes": [],
    })
    session = str(signal.get("session") or "unknown")
    setup = _setup_key(signal)
    conf = float(signal.get("confidence") or 0)
    row["seen"] = int(row.get("seen") or 0) + 1
    row["confidence_sum"] = float(row.get("confidence_sum") or 0) + conf
    row["average_confidence"] = round(row["confidence_sum"] / max(1, row["seen"]), 2)
    row["last_seen"] = _now()
    row["best_sessions"][session] = int(row["best_sessions"].get(session, 0)) + 1
    row["setup_counts"][setup] = int(row["setup_counts"].get(setup, 0)) + 1
    notes = list(row.get("personality_notes") or [])
    if symbol in {"XAUUSD", "GOLD"} and "gold_reserved_slot" not in notes:
        notes.append("gold_reserved_slot")
    if conf >= 90 and "high_confidence_seen" not in notes:
        notes.append("high_confidence_seen")
    row["personality_notes"] = notes[-10:]
    dna[symbol] = row
    _write_json(MARKET_DNA_FILE, dna)
    return row


def apply_cognitive_architecture(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Attach cognitive memory/ranking hints to every normal signal automatically."""
    try:
        row = _update_market_dna_from_signal(signal)
        symbol = _safe_symbol(signal)
        context = signal.get("market_context") or {}
        nn = signal.get("neural_network_brain") or {}
        ml = signal.get("hybrid_ml_confidence_engine") or {}
        p = signal.get("profitability_flywheel") or {}
        conf = float(signal.get("confidence") or 0)
        quality = str((signal.get("trade_quality_grades") or {}).get("overall") or "").upper()
        score = conf
        if quality == "A+":
            score += 4
        elif quality == "A":
            score += 2
        if nn.get("available") and float(nn.get("neural_probability") or 0) >= 80:
            score += 2
        if float(ml.get("ml_probability") or 0) >= 80:
            score += 2
        if int(context.get("context_score") or 0) >= 70:
            score += 2
        if p.get("decision") == "BLOCK":
            score -= 7
        score = max(0, min(100, round(score, 2)))
        signal["cognitive_architecture"] = {
            "active": True,
            "phase": "16",
            "market_dna_seen": row.get("seen"),
            "market_dna_average_confidence": row.get("average_confidence"),
            "opportunity_rank_score": score,
            "note": "Cognitive Architecture attached memory, market-DNA and verified-learning hints. Advisory only.",
        }
        if "smc_upgrade" in signal:
            try:
                if "cognitive architecture" not in signal["smc_upgrade"]:
                    signal["smc_upgrade"].append("cognitive architecture")
            except Exception:
                pass
    except Exception as exc:
        signal["cognitive_architecture"] = {"active": False, "error": str(exc), "note": "Cognitive layer skipped safely."}
    return signal


def _collect_existing_state() -> Dict[str, Any]:
    files = {
        "autopilot": Path("blue_autopilot_state.json"),
        "quota": Path("phase15_27_gold_reserved_quota_state.json"),
        "profitability": Path("phase15_22_profitability_flywheel_state.json"),
        "learning": Path("phase15_background_learning_status.json"),
        "neural": Path("phase15_19_neural_network_state.json"),
        "internet": Path("phase15_16_internet_learning_state.json"),
        "self_healing": Path("phase15_24_self_healing_state.json"),
    }
    return {k: _read_json(p, {}) for k, p in files.items()}


def run_cognitive_pulse(verbose: bool = False) -> Dict[str, Any]:
    """One safe cognition pass. Does not trade."""
    MEMORY_DIR.mkdir(exist_ok=True)
    started = _now()
    states = _collect_existing_state()
    world = _read_json(WORLD_MODEL_FILE, {})
    world.update({
        "updated_at": started,
        "major_symbols": _MAJOR_SYMBOLS,
        "current_focus": "verify profitable patterns, rank opportunities, protect trade quality",
        "autopilot_running": bool(str(states.get("autopilot", {})).strip("{}")),
        "learning_seen": bool(states.get("learning")),
        "internet_learning_seen": bool(states.get("internet")),
        "self_healing_seen": bool(states.get("self_healing")),
        "quota_policy": "2/day: one Gold slot + one Other-pair slot across London/NY",
        "safety_policy": "advisory learning only; execution still uses risk filters and Order Punch Shield",
    })
    _write_json(WORLD_MODEL_FILE, world)

    dna = _read_json(MARKET_DNA_FILE, {})
    verification = _read_json(VERIFICATION_QUEUE_FILE, {"items": []})
    items = list(verification.get("items") or [])
    # Add safe verification tasks, not blind trust.
    for item in [
        "Validate any new internet strategy lesson with backtest before trusting it.",
        "Compare confidence buckets 80-85, 85-90, 90+ against actual closed-trade results.",
        "Rank Gold separately from other pairs because Gold has a reserved quota slot.",
        "Replay no-trade decisions to learn if skipped A+ setups later moved profitably.",
    ]:
        if item not in [x.get("task") for x in items if isinstance(x, dict)]:
            items.append({"created_at": started, "task": item, "status": "queued", "source": "phase16"})
    verification["items"] = items[-100:]
    verification["updated_at"] = started
    _write_json(VERIFICATION_QUEUE_FILE, verification)

    replay = _read_json(EXPERIENCE_REPLAY_FILE, {"sessions": []})
    sessions = list(replay.get("sessions") or [])
    sessions.append({
        "at": started,
        "type": "background_cognitive_replay",
        "summary": "Reviewed available learning/autopilot/profitability states and refreshed world model.",
        "market_dna_symbols": len(dna),
        "verification_queue": len(verification.get("items") or []),
    })
    replay["sessions"] = sessions[-200:]
    replay["updated_at"] = started
    _write_json(EXPERIENCE_REPLAY_FILE, replay)

    st = _save_state(
        running=True,
        last_run=started,
        loop_count=int(_load_state().get("loop_count") or 0) + 1,
        last_message="Cognitive pulse completed: world model, market DNA, verification queue and replay refreshed.",
        last_error=None,
    )
    return {"ok": True, "ran": True, "message": st["last_message"], "at": started, "world_model": str(WORLD_MODEL_FILE)}


def _loop(print_fn: Optional[Callable[[str], None]] = None) -> None:
    _save_state(running=True, started_at=_now(), last_message="Cognitive Architecture background worker started.")
    # Quick startup pulse.
    try:
        res = run_cognitive_pulse(verbose=False)
        if print_fn:
            print_fn("Cognitive Architecture: " + str(res.get("message")))
    except Exception as exc:
        _save_state(last_error=str(exc), last_message="Cognitive pulse failed safely: " + str(exc))
    while not _stop_event.wait(max(300, COGNITIVE_INTERVAL_SECONDS)):
        try:
            run_cognitive_pulse(verbose=False)
        except Exception as exc:
            _save_state(last_error=str(exc), last_message="Cognitive pulse failed safely: " + str(exc))
    _save_state(running=False, stopped_at=_now(), last_message="Cognitive Architecture background worker stopped.")


def start_cognitive_architecture_service(print_fn: Optional[Callable[[str], None]] = None, force: bool = False) -> Dict[str, Any]:
    global _thread
    st = _load_state()
    if not force and not st.get("enabled", True):
        return {"ok": True, "started": False, "message": "Cognitive Architecture is OFF."}
    with _lock:
        if _thread and _thread.is_alive():
            return {"ok": True, "started": False, "message": "Cognitive Architecture already running."}
        _stop_event.clear()
        _thread = threading.Thread(target=_loop, kwargs={"print_fn": print_fn}, daemon=True, name="BlueCognitiveArchitecture")
        _thread.start()
    return {"ok": True, "started": True, "message": "Cognitive Architecture background worker started."}


def stop_cognitive_architecture_service() -> Dict[str, Any]:
    _stop_event.set()
    return {"ok": True, "message": "Cognitive Architecture stop requested."}


def cognitive_status_text() -> str:
    st = _load_state()
    world = _read_json(WORLD_MODEL_FILE, {})
    dna = _read_json(MARKET_DNA_FILE, {})
    verification = _read_json(VERIFICATION_QUEUE_FILE, {"items": []})
    return "\n".join([
        "Blue Cognitive Architecture Status",
        f"Running     : {st.get('running')}",
        f"Last run    : {st.get('last_run')}",
        f"Loop count  : {st.get('loop_count')}",
        f"Market DNA  : {len(dna)} symbol(s)",
        f"Verify queue: {len(verification.get('items') or [])} item(s)",
        f"World model : {world.get('current_focus', 'not built yet')}",
        f"Message     : {st.get('last_message')}",
    ])


def set_cognitive_architecture(enabled: bool) -> str:
    _save_state(enabled=bool(enabled))
    return "Cognitive Architecture is ON." if enabled else "Cognitive Architecture is OFF."
