"""Phase 15.2 background auto-learning service for Blue Forex Market AI.

This module starts a safe daemon worker when Blue launches. The worker keeps
checking for new closed journal/MT5/backtest trades while the terminal stays
usable. It is read-only for broker accounts: it imports learning rows and may
retrain ML, but it never places, modifies, or closes trades.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

try:
    from config import (
        PHASE15_BACKGROUND_AUTO_LEARN_ENABLED,
        PHASE15_BACKGROUND_INTERVAL_SECONDS,
        PHASE15_BACKGROUND_LEARN_ON_START,
        PHASE15_BACKGROUND_START_DELAY_SECONDS,
        PHASE15_BACKGROUND_PRINT_UPDATES,
        PHASE15_BACKGROUND_STATUS_FILE,
    )
except Exception:  # pragma: no cover - fallback for older configs
    PHASE15_BACKGROUND_AUTO_LEARN_ENABLED = True
    PHASE15_BACKGROUND_INTERVAL_SECONDS = 300
    PHASE15_BACKGROUND_LEARN_ON_START = True
    PHASE15_BACKGROUND_START_DELAY_SECONDS = 2
    PHASE15_BACKGROUND_PRINT_UPDATES = False
    PHASE15_BACKGROUND_STATUS_FILE = "phase15_background_learning_status.json"

try:
    from learning.auto_history_learning import run_startup_auto_learning, load_settings, update_status
except Exception:  # pragma: no cover
    run_startup_auto_learning = None  # type: ignore
    load_settings = None  # type: ignore
    update_status = None  # type: ignore

try:
    from knowledge.internet_learning import run_background_internet_learning_if_due
except Exception:  # pragma: no cover
    run_background_internet_learning_if_due = None  # type: ignore

try:
    from learning.neural_network_brain import run_background_neural_learning_if_due
except Exception:  # pragma: no cover
    run_background_neural_learning_if_due = None  # type: ignore


_Print = Optional[Callable[[str], None]]
_lock = threading.RLock()
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None
_state: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "stopped_at": None,
    "loop_count": 0,
    "total_new_rows": 0,
    "last_run": None,
    "last_message": "Background auto-learning has not started yet.",
    "last_error": None,
    "next_run_estimate": None,
}


def _utc_now() -> datetime:
    return datetime.utcnow()


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _save_background_status(extra: Optional[Dict[str, Any]] = None) -> None:
    data = dict(_state)
    if extra:
        data.update(extra)
    data["updated_at"] = _iso(_utc_now())
    try:
        with open(PHASE15_BACKGROUND_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def _load_background_status() -> Dict[str, Any]:
    if not os.path.exists(PHASE15_BACKGROUND_STATUS_FILE):
        return {}
    try:
        with open(PHASE15_BACKGROUND_STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _settings_allow_learning() -> bool:
    if not bool(PHASE15_BACKGROUND_AUTO_LEARN_ENABLED):
        return False
    try:
        settings = load_settings() if load_settings else {}
        return bool(settings.get("auto_learning_enabled", True))
    except Exception:
        return True


def run_background_learning_once(verbose: bool = False) -> Dict[str, Any]:
    """Run one safe background-learning pass now.

    This uses the Phase 15 import pipeline with duplicate protection, so repeated
    calls do not keep adding the same old trades.
    """
    started = _utc_now()
    if not _settings_allow_learning():
        res = {
            "ok": True,
            "ran": False,
            "new_rows": 0,
            "trained": False,
            "message": "Background auto-learning skipped because auto learning is OFF.",
            "at": _iso(started),
        }
    elif run_startup_auto_learning is None:
        res = {
            "ok": False,
            "ran": False,
            "new_rows": 0,
            "trained": False,
            "message": "Background auto-learning failed: Phase 15 importer is unavailable.",
            "at": _iso(started),
        }
    else:
        try:
            res = run_startup_auto_learning(verbose=verbose)
            # Phase 15.16: optional internet/environment learning in the same safe background loop.
            # This is read-only and due-guarded, so it does not spam the internet every cycle.
            if run_background_internet_learning_if_due is not None:
                try:
                    web_res = run_background_internet_learning_if_due()
                    res["internet_learning"] = web_res
                    if web_res.get("ran"):
                        res["message"] = str(res.get("message", "")) + " | " + str(web_res.get("message"))
                except Exception as web_exc:
                    res["internet_learning"] = {"ok": False, "ran": False, "error": str(web_exc), "message": "Internet learning skipped: " + str(web_exc)}
            # Phase 15.19: optional neural-network retraining in the same safe background loop.
            # This is advisory-only and never sends, closes, or modifies MT5 orders.
            if run_background_neural_learning_if_due is not None:
                try:
                    nn_res = run_background_neural_learning_if_due()
                    res["neural_learning"] = nn_res
                    if nn_res.get("ran"):
                        res["message"] = str(res.get("message", "")) + " | " + str(nn_res.get("message"))
                except Exception as nn_exc:
                    res["neural_learning"] = {"ok": False, "ran": False, "error": str(nn_exc), "message": "Neural learning skipped: " + str(nn_exc)}
            res["at"] = _iso(started)
        except Exception as exc:
            res = {
                "ok": False,
                "ran": False,
                "new_rows": 0,
                "trained": False,
                "message": f"Background auto-learning failed: {exc}",
                "error": str(exc),
                "at": _iso(started),
            }

    with _lock:
        _state["loop_count"] = int(_state.get("loop_count") or 0) + 1
        _state["last_run"] = _iso(started)
        _state["last_message"] = res.get("message", str(res))
        _state["last_error"] = res.get("error") if not res.get("ok", False) else None
        _state["total_new_rows"] = int(_state.get("total_new_rows") or 0) + int(res.get("new_rows") or 0)
        _state["last_result"] = res
        _save_background_status({"last_result": res})

    try:
        if update_status:
            update_status(last_background_auto_learning=res)
    except Exception:
        pass
    return res


def _background_loop(print_fn: _Print = None) -> None:
    interval = max(60, int(PHASE15_BACKGROUND_INTERVAL_SECONDS or 300))
    start_delay = max(0, int(PHASE15_BACKGROUND_START_DELAY_SECONDS or 0))
    with _lock:
        _state.update({
            "running": True,
            "started_at": _iso(_utc_now()),
            "stopped_at": None,
            "last_message": "Background auto-learning worker started.",
            "last_error": None,
        })
        _save_background_status()

    try:
        if bool(PHASE15_BACKGROUND_LEARN_ON_START):
            if _stop_event.wait(start_delay):
                return
            res = run_background_learning_once(verbose=False)
            if print_fn and bool(PHASE15_BACKGROUND_PRINT_UPDATES) and int(res.get("new_rows") or 0) > 0:
                print_fn("\n[Blue learning] " + str(res.get("message")))

        while not _stop_event.is_set():
            next_run = _utc_now() + timedelta(seconds=interval)
            with _lock:
                _state["next_run_estimate"] = _iso(next_run)
                _save_background_status()
            if _stop_event.wait(interval):
                break
            res = run_background_learning_once(verbose=False)
            if print_fn and bool(PHASE15_BACKGROUND_PRINT_UPDATES) and int(res.get("new_rows") or 0) > 0:
                print_fn("\n[Blue learning] " + str(res.get("message")))
    finally:
        with _lock:
            _state.update({
                "running": False,
                "stopped_at": _iso(_utc_now()),
                "next_run_estimate": None,
                "last_message": _state.get("last_message") or "Background auto-learning worker stopped.",
            })
            _save_background_status()


def start_background_learning_service(print_fn: _Print = None) -> Dict[str, Any]:
    """Start the daemon worker if it is not already running."""
    global _thread, _stop_event
    if not bool(PHASE15_BACKGROUND_AUTO_LEARN_ENABLED):
        return {"ok": True, "started": False, "message": "Background auto-learning is disabled in config.py."}
    if not _settings_allow_learning():
        return {"ok": True, "started": False, "message": "Background auto-learning is OFF. Use: auto learn on"}

    with _lock:
        if _thread and _thread.is_alive():
            return {"ok": True, "started": False, "message": "Background auto-learning is already running."}
        _stop_event = threading.Event()
        _thread = threading.Thread(target=_background_loop, args=(print_fn,), name="BlueBackgroundAutoLearning", daemon=True)
        _thread.start()
        interval = max(60, int(PHASE15_BACKGROUND_INTERVAL_SECONDS or 300))
        return {
            "ok": True,
            "started": True,
            "message": f"Background auto-learning started. It checks for new closed trades every {interval} seconds while Blue is running.",
        }


def stop_background_learning_service() -> Dict[str, Any]:
    """Stop the daemon worker for this running Blue session."""
    global _thread
    with _lock:
        if not _thread or not _thread.is_alive():
            _state["running"] = False
            _state["stopped_at"] = _iso(_utc_now())
            _save_background_status()
            return {"ok": True, "stopped": False, "message": "Background auto-learning is not running."}
        _stop_event.set()
        th = _thread
    th.join(timeout=3)
    with _lock:
        alive = th.is_alive()
        if not alive:
            _thread = None
        _state["running"] = bool(alive)
        _state["stopped_at"] = None if alive else _iso(_utc_now())
        _save_background_status()
    return {"ok": True, "stopped": not alive, "message": "Background auto-learning stopped." if not alive else "Stop requested; worker is finishing current import."}


def background_learning_status_text() -> str:
    """Human-readable terminal status for the background worker."""
    with _lock:
        live = dict(_state)
    saved = _load_background_status()
    merged = dict(saved)
    merged.update({k: v for k, v in live.items() if v is not None})
    interval = max(60, int(PHASE15_BACKGROUND_INTERVAL_SECONDS or 300))
    enabled = bool(PHASE15_BACKGROUND_AUTO_LEARN_ENABLED) and _settings_allow_learning()
    last_result = merged.get("last_result") if isinstance(merged.get("last_result"), dict) else {}
    last_new_rows = last_result.get("new_rows", 0) if last_result else 0
    trained = last_result.get("trained", False) if last_result else False
    return (
        "Phase 15.2 Background Auto Learning\n"
        f"Enabled in config/settings : {enabled}\n"
        f"Running in this session    : {bool(merged.get('running'))}\n"
        f"Check interval             : {interval} seconds\n"
        f"Learn immediately on start : {bool(PHASE15_BACKGROUND_LEARN_ON_START)}\n"
        f"Loop count                 : {merged.get('loop_count', 0)}\n"
        f"Total new rows this run    : {merged.get('total_new_rows', 0)}\n"
        f"Last run                   : {merged.get('last_run') or 'not yet'}\n"
        f"Last new rows              : {last_new_rows}\n"
        f"Last retrained             : {trained}\n"
        f"Next run estimate          : {merged.get('next_run_estimate') or 'not scheduled'}\n"
        f"Last message               : {merged.get('last_message') or 'none'}\n"
        f"Last error                 : {merged.get('last_error') or 'none'}\n"
        "Commands                   : background learn status | background learn now | background learn stop | background learn start"
    )
