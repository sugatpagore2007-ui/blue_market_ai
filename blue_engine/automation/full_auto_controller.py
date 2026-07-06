"""Phase 15.18 — Auto Everything + Parallel Voice/Text Command controller.

Goal:
- When Blue starts, the important systems run automatically.
- Text commands still work as manual controls/overrides.
- Order execution remains protected by MT5 demo-only and autopilot safety gates.

This controller does not open MT5, does not bypass risk filters, and does not let
internet learning or ML place trades directly. It only starts safe background
services that already have their own guardrails.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List

try:
    from config import (
        BLUE_AUTO_CORE_ENABLED,
        BLUE_AUTO_START_BACKGROUND_LEARNING,
        BLUE_AUTO_ENABLE_INTERNET_LEARNING,
        BLUE_AUTO_START_AUTOPILOT,
        BLUE_AUTO_START_VOICE_LISTENER,
        BLUE_AUTO_SCAN_SECONDS,
        BLUE_AUTO_STATUS_FILE,
        BLUE_AUTO_FORCE_DEMO_ONLY,
        AUTO_TRADE_DEMO_ONLY,
        AUTO_TRADE_ALLOW_REAL_ACCOUNT,
        MT5_AUTO_LAUNCH,
    )
except Exception:  # fallback for older configs
    BLUE_AUTO_CORE_ENABLED = True
    BLUE_AUTO_START_BACKGROUND_LEARNING = True
    BLUE_AUTO_ENABLE_INTERNET_LEARNING = True
    BLUE_AUTO_START_AUTOPILOT = True
    BLUE_AUTO_START_VOICE_LISTENER = False
    BLUE_AUTO_SCAN_SECONDS = 60
    BLUE_AUTO_STATUS_FILE = "phase15_18_parallel_voice_text_state.json"
    BLUE_AUTO_FORCE_DEMO_ONLY = True
    AUTO_TRADE_DEMO_ONLY = True
    AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
    MT5_AUTO_LAUNCH = False

try:
    from learning.background_auto_learning import (
        start_background_learning_service,
        stop_background_learning_service,
        background_learning_status_text,
        run_background_learning_once,
    )
except Exception:  # pragma: no cover
    start_background_learning_service = None  # type: ignore
    stop_background_learning_service = None  # type: ignore
    background_learning_status_text = None  # type: ignore
    run_background_learning_once = None  # type: ignore

try:
    from knowledge.internet_learning import (
        seed_default_internet_sources,
        set_internet_learning,
        internet_learning_report,
        run_background_internet_learning_if_due,
    )
except Exception:  # pragma: no cover
    seed_default_internet_sources = None  # type: ignore
    set_internet_learning = None  # type: ignore
    internet_learning_report = None  # type: ignore
    run_background_internet_learning_if_due = None  # type: ignore

try:
    from mt5_bridge.autopilot import autopilot_on, autopilot_off, autopilot_status
except Exception:  # pragma: no cover
    autopilot_on = None  # type: ignore
    autopilot_off = None  # type: ignore
    autopilot_status = None  # type: ignore

try:
    from voice.background_listener import start_background_voice, stop_background_voice, background_voice_status_text
except Exception:  # pragma: no cover
    start_background_voice = None  # type: ignore
    stop_background_voice = None  # type: ignore
    background_voice_status_text = None  # type: ignore

try:
    from voice.speaker import interrupt_speech
except Exception:  # pragma: no cover
    interrupt_speech = None  # type: ignore

try:
    from brain.cognitive_architecture import start_cognitive_architecture_service, stop_cognitive_architecture_service, cognitive_status_text, run_cognitive_pulse
except Exception:  # pragma: no cover
    start_cognitive_architecture_service = None  # type: ignore
    stop_cognitive_architecture_service = None  # type: ignore
    cognitive_status_text = None  # type: ignore
    run_cognitive_pulse = None  # type: ignore

try:
    from institutional.cme_group_brain import start_cme_group_brain_service, stop_cme_group_brain_service, cme_status_text, collect_cme_context
except Exception:  # pragma: no cover
    start_cme_group_brain_service = None  # type: ignore
    stop_cme_group_brain_service = None  # type: ignore
    cme_status_text = None  # type: ignore
    collect_cme_context = None  # type: ignore

try:
    from brain.autonomous_evolution import start_autonomous_evolution_service, stop_autonomous_evolution_service, evolution_status_text, run_evolution_pulse
except Exception:  # pragma: no cover
    start_autonomous_evolution_service = None  # type: ignore
    stop_autonomous_evolution_service = None  # type: ignore
    evolution_status_text = None  # type: ignore
    run_evolution_pulse = None  # type: ignore

_Print = Optional[Callable[[str], None]]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_state() -> Dict[str, Any]:
    default = {
        "full_auto_enabled": bool(BLUE_AUTO_CORE_ENABLED),
        "updated_at": None,
        "last_start": None,
        "last_stop": None,
        "last_results": [],
    }
    if not os.path.exists(BLUE_AUTO_STATUS_FILE):
        return default
    try:
        with open(BLUE_AUTO_STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if isinstance(data, dict):
            default.update(data)
    except Exception:
        pass
    return default


def _write_state(**updates: Any) -> Dict[str, Any]:
    st = _read_state()
    st.update(updates)
    st["updated_at"] = _now()
    try:
        with open(BLUE_AUTO_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, default=str)
    except Exception:
        pass
    return st


def set_full_auto_enabled(enabled: bool) -> str:
    _write_state(full_auto_enabled=bool(enabled))
    return "Full Auto Core is ON." if enabled else "Full Auto Core is OFF. Text commands still work."


def _append_result(results: List[str], label: str, message: Any) -> None:
    text = str(message)
    results.append(f"{label}: {text}")


def start_full_auto_mode(print_fn: _Print = None, command_handler: Optional[Callable[..., Any]] = None, force: bool = False) -> Dict[str, Any]:
    """Start all configured automatic systems without blocking terminal input."""
    st = _read_state()
    if not force and not st.get("full_auto_enabled", bool(BLUE_AUTO_CORE_ENABLED)):
        return {"ok": True, "started": False, "message": "Full Auto Core is OFF. Type: full auto on"}

    results: List[str] = []
    warnings: List[str] = []

    if bool(BLUE_AUTO_FORCE_DEMO_ONLY):
        if not bool(AUTO_TRADE_DEMO_ONLY) or bool(AUTO_TRADE_ALLOW_REAL_ACCOUNT):
            warnings.append("Safety warning: config should keep AUTO_TRADE_DEMO_ONLY=True and AUTO_TRADE_ALLOW_REAL_ACCOUNT=False for automatic mode.")
    if bool(MT5_AUTO_LAUNCH):
        warnings.append("Safety warning: MT5_AUTO_LAUNCH should stay False. Blue should attach to already-open MT5 only.")

    # 1) Internet/environment learning setup. Read-only.
    if bool(BLUE_AUTO_ENABLE_INTERNET_LEARNING):
        try:
            if seed_default_internet_sources:
                seed = seed_default_internet_sources()
                _append_result(results, "Internet sources", seed.get("message", seed))
            if set_internet_learning:
                msg = set_internet_learning(True, background=True)
                _append_result(results, "Internet learning", msg)
        except Exception as exc:
            _append_result(results, "Internet learning", f"skipped: {exc}")

    # 2) Background learning: MT5/journal/backtest + due-guarded internet learning.
    if bool(BLUE_AUTO_START_BACKGROUND_LEARNING):
        try:
            if start_background_learning_service:
                res = start_background_learning_service(print_fn=print_fn)
                _append_result(results, "Background learning", res.get("message", res))
            else:
                _append_result(results, "Background learning", "unavailable")
        except Exception as exc:
            _append_result(results, "Background learning", f"skipped: {exc}")

    # 3) Autopilot: terminal background thread. Demo-only safety remains inside executor.
    if bool(BLUE_AUTO_START_AUTOPILOT):
        try:
            if autopilot_on:
                msg = autopilot_on(scan_seconds=int(BLUE_AUTO_SCAN_SECONDS))
                _append_result(results, "Autopilot", msg)
            else:
                _append_result(results, "Autopilot", "unavailable")
        except Exception as exc:
            _append_result(results, "Autopilot", f"skipped: {exc}")

    # 4) Phase 16: cognitive architecture auto worker. Advisory only; never places orders.
    try:
        if start_cognitive_architecture_service:
            cog = start_cognitive_architecture_service(print_fn=print_fn)
            _append_result(results, "Cognitive Architecture", cog.get("message", cog))
        else:
            _append_result(results, "Cognitive Architecture", "unavailable")
    except Exception as exc:
        _append_result(results, "Cognitive Architecture", f"skipped: {exc}")

    # 4b) Phase 16.1: CME Group institutional context worker. Advisory only; never places orders.
    try:
        if start_cme_group_brain_service:
            cme = start_cme_group_brain_service(print_fn=print_fn)
            _append_result(results, "CME Group Brain", cme.get("message", cme))
        else:
            _append_result(results, "CME Group Brain", "unavailable")
    except Exception as exc:
        _append_result(results, "CME Group Brain", f"skipped: {exc}")

    # 4c) Phase 16.2: Autonomous Evolution Engine. Weekly reports + verified learning; advisory only.
    try:
        if start_autonomous_evolution_service:
            evo = start_autonomous_evolution_service(print_fn=print_fn)
            _append_result(results, "Autonomous Evolution", evo.get("message", evo))
        else:
            _append_result(results, "Autonomous Evolution", "unavailable")
    except Exception as exc:
        _append_result(results, "Autonomous Evolution", f"skipped: {exc}")

    # 5) Phase 15.18: voice can auto-start. If mic packages fail, text terminal still works.
    if bool(BLUE_AUTO_START_VOICE_LISTENER) and command_handler is not None:
        try:
            if start_background_voice:
                res = start_background_voice(command_handler, print_fn=print_fn, speak_ready=False)
                _append_result(results, "Voice listener", res.get("message", res))
            else:
                _append_result(results, "Voice listener", "unavailable")
        except Exception as exc:
            _append_result(results, "Voice listener", f"skipped: {exc}")
    else:
        _append_result(results, "Voice listener", "OFF by config. Type: voice")

    _write_state(last_start=_now(), last_results=results, last_warnings=warnings)
    message = "Full Auto Core started. Text commands are still active."
    return {"ok": True, "started": True, "message": message, "results": results, "warnings": warnings}


def stop_full_auto_mode(disable_autostart: bool = False) -> Dict[str, Any]:
    """Stop background loops for this session. Text command loop stays alive."""
    parts: List[str] = []
    try:
        if autopilot_off:
            parts.append("Autopilot: " + str(autopilot_off()))
    except Exception as exc:
        parts.append("Autopilot stop skipped: " + str(exc))
    try:
        if stop_background_learning_service:
            res = stop_background_learning_service()
            parts.append("Background learning: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Background learning stop skipped: " + str(exc))
    try:
        if stop_cognitive_architecture_service:
            res = stop_cognitive_architecture_service()
            parts.append("Cognitive Architecture: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Cognitive stop skipped: " + str(exc))
    try:
        if stop_cme_group_brain_service:
            res = stop_cme_group_brain_service()
            parts.append("CME Group Brain: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("CME stop skipped: " + str(exc))
    try:
        if stop_autonomous_evolution_service:
            res = stop_autonomous_evolution_service()
            parts.append("Autonomous Evolution: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Evolution stop skipped: " + str(exc))
    try:
        if stop_background_voice:
            res = stop_background_voice()
            parts.append("Voice listener: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Voice stop skipped: " + str(exc))
    try:
        if interrupt_speech:
            interrupt_speech()
            parts.append("Voice speech: interrupted.")
    except Exception:
        pass
    updates: Dict[str, Any] = {"last_stop": _now(), "last_stop_results": parts}
    if disable_autostart:
        updates["full_auto_enabled"] = False
    _write_state(**updates)
    return {"ok": True, "message": "\n".join(parts) if parts else "No automatic services were running.", "results": parts}


def run_full_auto_now(print_fn: _Print = None) -> Dict[str, Any]:
    """One manual pulse: learning now + due internet check. Does not force an order."""
    parts: List[str] = []
    try:
        if run_background_learning_once:
            res = run_background_learning_once(verbose=True)
            parts.append("Background learning now: " + str(res.get("message", res)))
        else:
            parts.append("Background learning now: unavailable")
    except Exception as exc:
        parts.append("Background learning now skipped: " + str(exc))
    try:
        if run_cognitive_pulse:
            res = run_cognitive_pulse(verbose=True)
            parts.append("Cognitive Architecture now: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Cognitive Architecture now skipped: " + str(exc))
    try:
        if collect_cme_context:
            res = collect_cme_context(force=True)
            parts.append("CME Group Brain now: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("CME Group Brain now skipped: " + str(exc))
    try:
        if run_evolution_pulse:
            res = run_evolution_pulse(force_monday_report=True)
            parts.append("Autonomous Evolution now: " + str(res.get("message", res)))
    except Exception as exc:
        parts.append("Autonomous Evolution now skipped: " + str(exc))
    try:
        if run_background_internet_learning_if_due:
            res = run_background_internet_learning_if_due(force=True)  # supported in this build? fallback below
            parts.append("Internet learning now: " + str(res.get("message", res)))
    except TypeError:
        try:
            res = run_background_internet_learning_if_due()
            parts.append("Internet learning due-check: " + str(res.get("message", res)))
        except Exception as exc:
            parts.append("Internet learning now skipped: " + str(exc))
    except Exception as exc:
        parts.append("Internet learning now skipped: " + str(exc))
    msg = "\n".join(parts)
    if print_fn:
        print_fn(msg)
    return {"ok": True, "message": msg, "results": parts}


def full_auto_status_text() -> str:
    st = _read_state()
    lines = [
        "Blue Full Auto Core Status",
        f"Full Auto Core        : {'ON' if st.get('full_auto_enabled') else 'OFF'}",
        f"Last start            : {st.get('last_start')}",
        f"Last stop             : {st.get('last_stop')}",
        f"Text commands active  : YES",
        f"MT5 auto launch       : {MT5_AUTO_LAUNCH} (should stay False)",
        f"Demo-only auto trading: {AUTO_TRADE_DEMO_ONLY}",
        f"Real auto allowed     : {AUTO_TRADE_ALLOW_REAL_ACCOUNT}",
        f"Auto scan seconds     : {BLUE_AUTO_SCAN_SECONDS}",
        "",
        "Startup systems:",
        f"- Background learning : {BLUE_AUTO_START_BACKGROUND_LEARNING}",
        f"- Internet learning   : {BLUE_AUTO_ENABLE_INTERNET_LEARNING}",
        f"- Autopilot           : {BLUE_AUTO_START_AUTOPILOT}",
        f"- Voice listener      : {BLUE_AUTO_START_VOICE_LISTENER} (Phase 15.18 parallel voice + text)",
    ]
    last = st.get("last_results") or []
    if last:
        lines.append("")
        lines.append("Last startup result:")
        lines.extend(["- " + str(x) for x in last])
    warnings = st.get("last_warnings") or []
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(["- " + str(x) for x in warnings])
    try:
        if background_learning_status_text:
            lines.append("\n" + background_learning_status_text())
    except Exception as exc:
        lines.append(f"\nBackground status unavailable: {exc}")
    try:
        if autopilot_status:
            lines.append("\n" + autopilot_status())
    except Exception as exc:
        lines.append(f"\nAutopilot status unavailable: {exc}")
    try:
        if cognitive_status_text:
            lines.append("\n" + cognitive_status_text())
    except Exception as exc:
        lines.append(f"\nCognitive status unavailable: {exc}")
    try:
        if cme_status_text:
            lines.append("\n" + cme_status_text())
    except Exception as exc:
        lines.append(f"\nCME status unavailable: {exc}")
    try:
        if evolution_status_text:
            lines.append("\n" + evolution_status_text())
    except Exception as exc:
        lines.append(f"\nEvolution status unavailable: {exc}")
    try:
        if background_voice_status_text:
            lines.append("\n" + background_voice_status_text())
    except Exception:
        pass
    return "\n".join(lines)


def basic_auto_commands_text() -> str:
    return """Blue Auto + Text Command Mode

Automatic after python main.py:
  - Background learning starts.
  - Internet/environment learning is enabled and due-checked.
  - Autopilot starts in background.
  - Auto manager runs inside autopilot cycles.
  - Cognitive Architecture learns/ranks/verifies in background.
  - CME Group Brain adds institutional futures context in background.
  - Autonomous Evolution Engine creates Monday reports and verifies learning in background.
  - Voice listener starts only if enabled; default is OFF.
  - Text terminal stays open for commands at the same time.

Basic text commands to control everything:
  status / auto status        -> full automatic system status
  stop / stop everything      -> stop autopilot + background learning + voice
  full auto on                -> enable and start all automatic systems
  full auto off               -> stop and disable auto-start for next runs
  auto now                    -> run one learning/background pulse now
  order doctor gold           -> diagnose why order can/cannot punch
  broker / connect mt5        -> broker and MT5 connection check
  account / balance           -> MT5 account info
  risk                        -> save manual risk settings
  voice / talk                -> start/resume parallel voice listener
  help                        -> full command list
  exit                        -> close Blue

Manual text + voice commands still work:
  gold / eurusd / btc / best / scan / why / internet report / win rate

Safety:
  Full auto does not open MT5. Keep MT5 open manually and logged in.
  Auto execution stays demo-only unless you deliberately change config.py.
"""
