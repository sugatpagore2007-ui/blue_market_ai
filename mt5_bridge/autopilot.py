"""
Blue Autopilot controller.

One-command automation:
- connects to MT5 terminal-only
- confirms auto execution / auto manager settings
- scans all supported pairs
- auto executes only if guardrails pass
- manages open Blue trades each cycle
- logs everything in the VS Code terminal

Important: this module never launches or pops up MT5. Keep MT5 open manually.
Phase 7.6.5 change: autopilot runs in a background thread, so you can still
enter commands in the VS Code terminal while it is scanning.
"""
from __future__ import annotations

import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from config import (
    AUTO_ORDER_EXECUTION,
    MIN_AUTO_TRADE_CONFIDENCE,
    AUTO_TRADE_DEMO_ONLY,
    AUTO_TRADE_RISK_PERCENT,
    MAX_AUTO_TRADES_PER_DAY,
    MAX_DAILY_LOSS_PERCENT,
    AUTO_MANAGER_ENABLED,
    AUTO_MANAGER_CHECK_SECONDS,
)
try:
    from config import MAX_SPREAD_POINTS_BY_SYMBOL, MAX_SPREAD_POINTS
except Exception:
    MAX_SPREAD_POINTS_BY_SYMBOL = {}
    MAX_SPREAD_POINTS = 80

try:
    from config import (
        AUTOPILOT_ONLY_BEST_TRADE, AUTOPILOT_MIN_SETUP_GRADE, AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE,
        AUTOPILOT_SHOW_SIGNAL_WHEN_BLOCKED, AUTOPILOT_SHOW_BLOCK_REASON,
        AUTOPILOT_DEFAULT_SYMBOLS, AUTOPILOT_TRY_ALL_ELIGIBLE_CANDIDATES,
        AUTOPILOT_SHOW_TRADE_BASIS, AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS
    )
except Exception:
    AUTOPILOT_ONLY_BEST_TRADE = True
    AUTOPILOT_MIN_SETUP_GRADE = 'A+'
    AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE = 1
    AUTOPILOT_SHOW_SIGNAL_WHEN_BLOCKED = True
    AUTOPILOT_SHOW_BLOCK_REASON = True
    AUTOPILOT_DEFAULT_SYMBOLS = ["xauusd", "xagusd", "ethusd", "btcusd", "usoil", "usdjpy", "eurusd", "ustec", "gbpusd"]
    AUTOPILOT_TRY_ALL_ELIGIBLE_CANDIDATES = True
    AUTOPILOT_SHOW_TRADE_BASIS = True
    AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS = False

from .terminal import ensure_connected
from .auto_executor import auto_status_text, execute_signal_if_allowed
from .auto_manager import auto_manager_status, manage_once, start_auto_manager_background, auto_manager_background_status
from .background_trade_events import format_autopilot_trade_opened_card, handle_autopilot_trade_opened
from utils.symbols import resolve_symbol
from analysis.signal_engine import build_signal
from storage.database import save_signal
from voice.speaker import speak
try:
    from utils.trade_reasoning import format_terminal_reason_card
except Exception:
    format_terminal_reason_card = None

try:
    from brain.autonomous_evolution import autopilot_cycle_pulse, on_autopilot_order_punched
except Exception:
    autopilot_cycle_pulse = None  # type: ignore
    on_autopilot_order_punched = None  # type: ignore

AUTOPILOT_STATE_FILE = "blue_autopilot_state.json"
AUTOPILOT_SYMBOLS: List[str] = list(AUTOPILOT_DEFAULT_SYMBOLS)
DEFAULT_SCAN_SECONDS = 300
DEFAULT_CYCLES = 999999

_AUTOPILOT_THREAD: Optional[threading.Thread] = None
_AUTOPILOT_LOCK = threading.Lock()


def _load_state() -> Dict[str, Any]:
    if not os.path.exists(AUTOPILOT_STATE_FILE):
        return {"enabled": False, "updated_at": None}
    try:
        with open(AUTOPILOT_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "updated_at": None}


def _save_state(enabled: bool) -> None:
    with open(AUTOPILOT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"enabled": bool(enabled), "updated_at": datetime.now().isoformat(timespec="seconds")}, f, indent=2)


def _thread_alive() -> bool:
    return _AUTOPILOT_THREAD is not None and _AUTOPILOT_THREAD.is_alive()


def autopilot_status() -> str:
    st = _load_state()
    return (
        "Blue Autopilot Status\n"
        f"State                         : {'ON' if st.get('enabled') else 'OFF'}\n"
        f"Background thread active       : {'YES' if _thread_alive() else 'NO'}\n"
        f"Updated at                    : {st.get('updated_at')}\n"
        f"Symbols                       : {', '.join(AUTOPILOT_SYMBOLS)}\n"
        f"Auto execution enabled         : {AUTO_ORDER_EXECUTION}\n"
        f"Minimum confidence             : {MIN_AUTO_TRADE_CONFIDENCE}%\n"
        f"Demo-only protection           : {AUTO_TRADE_DEMO_ONLY}\n"
        f"Auto risk per trade            : {AUTO_TRADE_RISK_PERCENT}%\n"
        f"Max auto trades per day        : {MAX_AUTO_TRADES_PER_DAY}\n"
        f"Max daily loss guard           : {MAX_DAILY_LOSS_PERCENT}%\n"
        f"Default max spread points      : {MAX_SPREAD_POINTS}\n"
        f"Asset spread limits            : {MAX_SPREAD_POINTS_BY_SYMBOL}\n"
        f"Auto manager enabled           : {AUTO_MANAGER_ENABLED}\n"
        f"Best-trade-only autopilot    : {AUTOPILOT_ONLY_BEST_TRADE}\n"
        f"Required setup grade          : {AUTOPILOT_MIN_SETUP_GRADE}\n"
        f"Max new trades per cycle      : {AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE}\n"
        f"Auto manager check seconds     : {AUTO_MANAGER_CHECK_SECONDS}\n\n"
        + auto_status_text()
        + "\n\n"
        + auto_manager_status()
        + "\n\n"
        + auto_manager_background_status()
    )


def autopilot_off() -> str:
    _save_state(False)
    return "Blue autopilot is OFF. Background loop will stop after the current cycle/sleep."



def _grade_value(grade: str) -> int:
    order = {'A+': 6, 'A': 5, 'B+': 4, 'B': 3, 'C': 2, 'D': 1}
    return order.get(str(grade or '').upper().strip(), 0)


def _overall_grade(result: Dict[str, Any]) -> str:
    grades = result.get('trade_quality_grades') or {}
    return str(grades.get('overall') or grades.get('setup') or result.get('setup_grade') or '').upper().strip()


def _signal_direction(result: Dict[str, Any]) -> str:
    """Market direction shown to the user. Execution can still be WAIT/BLOCK."""
    for k in [
        'signal_direction',
        'original_action_before_no_trade',
        'action_before_dataset_ml',
        'action_before_video_knowledge',
        'action_before_candlestick',
        'action_after_confidence_filter',
        'base_action_before_filters',
        'action',
    ]:
        v = str(result.get(k, '')).upper().strip()
        if v in ['BUY', 'SELL']:
            return v
    return 'WAIT'


def _block_reason(result: Dict[str, Any]) -> str:
    reasons = []
    filt = result.get('a_plus_filter') or {}
    if filt and not filt.get('allow_autopilot', False):
        reasons.append(str(filt.get('reason') or 'A+ filter blocked'))
    nt = result.get('no_trade_intelligence') or {}
    if nt and not nt.get('allow_trade', True):
        reasons.append(str(nt.get('note') or 'No-trade brain blocked'))
    ds = result.get('dataset_ml_engine') or {}
    if str(ds.get('decision', '')).startswith('BLOCK'):
        reasons.append(str(ds.get('decision')))
    vk = result.get('video_knowledge_engine') or {}
    if str(vk.get('decision', '')).startswith('BLOCK'):
        reasons.append(str(vk.get('decision')))
    vote = result.get('multi_agent_voting') or {}
    if str(vote.get('decision', '')).upper() == 'REJECT':
        reasons.append('multi-agent voting rejected')
    if not reasons and str(result.get('action','WAIT')).upper() == 'WAIT':
        reasons.append(str(result.get('autopilot_display_note') or 'execution action is WAIT'))
    return ' | '.join([r for r in reasons if r])[:260]




def _autopilot_trade_basis(result: Dict[str, Any], mode: str = "candidate") -> str:
    """Return a clean reason card for autopilot decisions.

    The normal `format_terminal_reason_card()` is used when available, then this
    adds an autopilot-specific header so the terminal clearly shows why Blue is
    taking or skipping the trade during autopilot.
    """
    symbol = result.get('symbol', 'UNKNOWN')
    action = _signal_direction(result)
    execution_action = str(result.get('action', 'WAIT')).upper()
    grade = _overall_grade(result) or 'N/A'
    filt = result.get('a_plus_filter') or {}
    pass_text = 'PASS' if filt.get('allow_autopilot') else 'BLOCK'
    block = _block_reason(result)
    lines = []
    lines.append("\nAUTOPILOT TRADE BASIS / WHY BLUE SELECTED THIS SETUP")
    lines.append("=" * 80)
    lines.append(f"Symbol        : {symbol}")
    lines.append(f"Signal        : {action}")
    lines.append(f"Auto action   : {execution_action}")
    lines.append(f"Confidence    : {result.get('confidence')}%")
    lines.append(f"Grade         : {grade}")
    lines.append(f"Auto filter   : {pass_text}")
    if block:
        lines.append(f"Block reason  : {block}")
    lines.append(f"Entry plan    : entry {result.get('entry')} | SL {result.get('stop_loss')} | TP1 {result.get('target_1')} | TP2 {result.get('target_2')}")

    # Add the full reason card already built for normal typed analysis.
    if format_terminal_reason_card:
        try:
            card_text = format_terminal_reason_card(result).strip()
            if card_text:
                lines.append(card_text)
        except Exception as exc:
            lines.append(f"Reason card   : unavailable ({exc})")
    else:
        analyst = result.get('analyst_reason') or result.get('human_read') or ''
        if analyst:
            lines.append("Analyst basis : " + str(analyst)[:900])

    lines.append("=" * 80)
    return "\n".join(lines)

def _is_a_plus_candidate(result: Dict[str, Any]) -> bool:
    action = str(result.get('action', 'WAIT')).upper()
    if action not in ['BUY', 'SELL']:
        return False
    confidence = float(result.get('confidence', 0) or 0)
    if confidence < float(MIN_AUTO_TRADE_CONFIDENCE):
        return False
    required = str(AUTOPILOT_MIN_SETUP_GRADE or '').upper().strip()
    grade = _overall_grade(result)
    if grade and required and _grade_value(grade) < _grade_value(required):
        return False
    # Phase 15.23: respect the final smart A/A+ filter, but do not separately
    # block only because a soft advisory agent voted REJECT. The smart filter
    # already converts multi-agent/portfolio/news warnings into hard blocks only
    # when confidence/ML/grade are not strong enough.
    phase9_filter = result.get('a_plus_filter') or {}
    if phase9_filter and not phase9_filter.get('allow_autopilot', False):
        return False
    return True


def _candidate_rank(result: Dict[str, Any]) -> tuple:
    p = result.get('probability_engine') or {}
    ml = result.get('hybrid_ml_confidence_engine') or {}
    vote = result.get('multi_agent_voting') or {}
    tp_prob = float(p.get('tp1_probability', 0) or p.get('probability_tp1', 0) or p.get('tp1', 0) or 0)
    ml_score = float(ml.get('final_trade_score', 0) or ml.get('ml_probability', 0) or 0)
    votes = int(vote.get('votes_for_trade', 0) or 0)
    grade = _overall_grade(result)
    confidence = float(result.get('confidence', 0) or 0)
    return (_grade_value(grade), ml_score, votes, confidence, tp_prob)


def _analyze_symbol(symbol_text: str) -> Dict[str, Any]:
    name, ticker = resolve_symbol(symbol_text)
    if not ticker:
        return {'symbol': symbol_text, 'action': 'WAIT', 'confidence': 0, 'error': 'unsupported symbol'}
    result = build_signal(name, ticker, account=None, trade_style='intraday')
    save_signal(result)
    return result


def _line_for_result(result: Dict[str, Any]) -> str:
    if result.get('error'):
        return f"{result.get('symbol')}: {result.get('error')}"
    grade = _overall_grade(result) or 'N/A'
    ml = result.get('hybrid_ml_confidence_engine') or {}
    ml_score = ml.get('final_trade_score', '?')
    filt = result.get('a_plus_filter') or {}
    fstate = 'PASS' if filt.get('allow_autopilot') else 'BLOCK'
    signal = _signal_direction(result) if AUTOPILOT_SHOW_SIGNAL_WHEN_BLOCKED else str(result.get('action', 'WAIT')).upper()
    execution = str(result.get('action', 'WAIT')).upper()
    prefix = f"{result.get('symbol')}: SIGNAL {signal}"
    if execution != signal:
        prefix += f" | auto {execution}"
    reason = _block_reason(result) if AUTOPILOT_SHOW_BLOCK_REASON and fstate == 'BLOCK' else ''
    base = (
        f"{prefix} | confidence {result.get('confidence')}% | grade {grade} | ML {ml_score}% | AUTO FILTER {fstate} | "
        f"entry {result.get('entry')} | SL {result.get('stop_loss')} | TP1 {result.get('target_1')} | TP2 {result.get('target_2')}"
    )
    if reason:
        base += f" | block reason: {reason}"
    return base

def _scan_symbol(symbol_text: str) -> str:
    name, ticker = resolve_symbol(symbol_text)
    if not ticker:
        return f"{symbol_text}: unsupported symbol."
    result = build_signal(name, ticker, account=None, trade_style="intraday")
    save_signal(result)
    line = f"{name}: {result.get('action')} | confidence {result.get('confidence')}% | entry {result.get('entry')} | SL {result.get('stop_loss')} | TP1 {result.get('target_1')} | TP2 {result.get('target_2')}"
    print(line, flush=True)
    if str(result.get("action", "WAIT")).upper() != "WAIT":
        exec_msg = execute_signal_if_allowed(result)
        print(exec_msg, flush=True)
        if "AUTO TRADE DONE" in exec_msg:
            _print_order_punched_card(result, exec_msg)
            try:
                handle_autopilot_trade_opened(result, exec_msg, print_fn=print)
            except Exception as exc:
                print(f"Phase 16.3 background trade event skipped safely: {exc}", flush=True)
            speak(f"Auto trade sent for {name}. Confidence {result.get('confidence')} percent. Auto manager is active.", block=False)
        elif float(result.get("confidence", 0) or 0) >= float(MIN_AUTO_TRADE_CONFIDENCE):
            speak(f"{name} reached auto threshold, but order was skipped. {exec_msg[:180]}", block=False)
        return line + "\n" + exec_msg
    return line



def _print_order_punched_card(result: Dict[str, Any], exec_msg: str) -> None:
    """Immediate clear card after order is punched. Does not wait for cycle end."""
    if "AUTO TRADE DONE" not in str(exec_msg):
        return
    print(format_autopilot_trade_opened_card(result, exec_msg), flush=True)

def _sleep_with_stop(total_seconds: int) -> None:
    """Sleep in small chunks so 'blue autopilot off' responds faster."""
    end_time = time.time() + max(1, int(total_seconds))
    while time.time() < end_time and _load_state().get("enabled"):
        time.sleep(1)


def _autopilot_loop(scan_seconds: int = DEFAULT_SCAN_SECONDS, cycles: int = DEFAULT_CYCLES) -> None:
    ok, msg = ensure_connected()
    header = [
        "Blue autopilot background loop started.",
        "Terminal-only mode: MT5 must already be open. Blue will not launch or pop up MT5.",
        msg,
        "Safety guards active: confidence threshold, demo-only guard, real-account lock, max trades/day, daily loss guard, spread guard.",
        "You can keep typing commands in this same terminal. Use 'blue autopilot off' to stop.",
    ]
    print("\n" + "\n".join(header), flush=True)
    speak("Blue autopilot is on in background mode. You can still type commands in the terminal.", block=False)
    try:
        print(start_auto_manager_background(), flush=True)
    except Exception as exc:
        print(f"Auto manager background start error: {exc}", flush=True)

    last_summary = ""
    try:
        for cycle in range(1, int(cycles) + 1):
            if not _load_state().get("enabled"):
                break
            print("\n" + "=" * 80, flush=True)
            print(f"AUTOPILOT CYCLE {cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
            print("=" * 80, flush=True)

            cycle_lines = []
            if AUTOPILOT_ONLY_BEST_TRADE:
                analyzed = []
                print('Scanning all pairs first. Autopilot will enter only the strongest eligible demo setup this cycle.', flush=True)
                for symbol in AUTOPILOT_SYMBOLS:
                    if not _load_state().get("enabled"):
                        break
                    try:
                        result = _analyze_symbol(symbol)
                        analyzed.append(result)
                        line = _line_for_result(result)
                        print(line, flush=True)
                        if AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS and _signal_direction(result) in ['BUY', 'SELL']:
                            basis = _autopilot_trade_basis(result, mode='scan')
                            print(basis, flush=True)
                            cycle_lines.append(basis)
                        cycle_lines.append(line)
                    except Exception as e:
                        err = f"{symbol}: autopilot scan error: {e}"
                        print(err, flush=True)
                        cycle_lines.append(err)

                try:
                    if autopilot_cycle_pulse:
                        autopilot_cycle_pulse(cycle, analyzed=analyzed, print_fn=print)
                except Exception as exc:
                    print(f"Phase 16.2 evolution pulse skipped safely: {exc}", flush=True)

                candidates = [r for r in analyzed if _is_a_plus_candidate(r)]
                candidates.sort(key=_candidate_rank, reverse=True)
                max_new = max(1, int(AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE))

                if not candidates:
                    msg = f"No autopilot execution this cycle. Blue may still show SIGNAL BUY/SELL above, but auto entry needs confidence >= {MIN_AUTO_TRADE_CONFIDENCE}%, grade >= {AUTOPILOT_MIN_SETUP_GRADE}, execution enabled, demo-only guard passing, and all safety filters passing."
                    print(msg, flush=True)
                    cycle_lines.append(msg)

                # Phase 15.11 hotfix:
                # Earlier builds chose only the top-ranked setup before checking whether the
                # broker actually had/selectable MT5 symbol for that instrument. If NASDAQ
                # mapped to NAS100m but the account used a different name, Blue stopped with
                # "Could not select MT5 symbol NAS100m" even though other valid setups existed.
                # Now Blue tries candidates in rank order until one order is actually sent, or
                # all candidates are skipped with clear reasons.
                successful_orders = 0
                attempted_orders = 0
                for result in candidates:
                    if successful_orders >= max_new:
                        break
                    name = result.get('symbol')
                    attempted_orders += 1
                    decision = f"Chosen autopilot candidate #{attempted_orders}: {name} {result.get('action')} | confidence {result.get('confidence')}% | grade {_overall_grade(result) or 'N/A'}"
                    print(decision, flush=True)
                    if AUTOPILOT_SHOW_TRADE_BASIS:
                        basis = _autopilot_trade_basis(result, mode='candidate')
                        print(basis, flush=True)
                        cycle_lines.append(basis)
                    exec_msg = execute_signal_if_allowed(result)
                    print(exec_msg, flush=True)
                    cycle_lines.append(decision + "\n" + exec_msg)
                    if "AUTO TRADE DONE" in exec_msg:
                        successful_orders += 1
                        _print_order_punched_card(result, exec_msg)
                        try:
                            if on_autopilot_order_punched:
                                ev = on_autopilot_order_punched(result, exec_msg)
                                print(ev.get('message', ev), flush=True)
                        except Exception as exc:
                            print(f"Phase 16.2 post-order reflection skipped safely: {exc}", flush=True)
                        try:
                            handle_autopilot_trade_opened(result, exec_msg, print_fn=print)
                        except Exception as exc:
                            print(f"Phase 16.3 background trade event skipped safely: {exc}", flush=True)
                        speak(f"Autopilot selected a valid setup: {name}. Trade sent. Auto manager is active.", block=False)
                    else:
                        # Keep going if the chosen instrument is not available, already open,
                        # or fails broker-side execution checks. The next ranked candidate may work.
                        speak(f"Autopilot skipped {name}. Trying next eligible setup if available.", block=False)

                if candidates and successful_orders == 0:
                    msg = "No order was sent after checking all eligible candidates. Read the AUTO TRADE SKIPPED/FAILED line above for the exact broker reason."
                    print(msg, flush=True)
                    cycle_lines.append(msg)
            else:
                for symbol in AUTOPILOT_SYMBOLS:
                    if not _load_state().get("enabled"):
                        break
                    try:
                        cycle_lines.append(_scan_symbol(symbol))
                    except Exception as e:
                        err = f"{symbol}: autopilot scan error: {e}"
                        print(err, flush=True)
                        cycle_lines.append(err)

            try:
                manager_msg = manage_once()
                print("\n" + manager_msg, flush=True)
                cycle_lines.append(manager_msg)
            except Exception as e:
                manager_msg = f"Auto manager error: {e}"
                print(manager_msg, flush=True)
                cycle_lines.append(manager_msg)

            last_summary = "\n".join(cycle_lines[-5:])
            if cycle < int(cycles) and _load_state().get("enabled"):
                print(f"\nNext autopilot scan in {scan_seconds} seconds. You can type commands now. Use 'blue autopilot off' to stop.", flush=True)
                _sleep_with_stop(max(10, int(scan_seconds)))
    except KeyboardInterrupt:
        _save_state(False)
        print("Blue autopilot stopped by keyboard interrupt.", flush=True)
    finally:
        _save_state(False)
        speak("Blue autopilot is off.", block=False)
        print("Blue autopilot stopped.\n" + last_summary, flush=True)


def autopilot_on(scan_seconds: int = DEFAULT_SCAN_SECONDS, cycles: int = DEFAULT_CYCLES) -> str:
    """Start terminal-only autopilot in background so main input remains usable."""
    global _AUTOPILOT_THREAD
    with _AUTOPILOT_LOCK:
        if _thread_alive() and _load_state().get("enabled"):
            return "Blue autopilot is already running in background. You can still type commands. Use 'blue autopilot off' to stop."
        _save_state(True)
        _AUTOPILOT_THREAD = threading.Thread(
            target=_autopilot_loop,
            kwargs={"scan_seconds": scan_seconds, "cycles": cycles},
            daemon=True,
            name="BlueAutopilotThread",
        )
        _AUTOPILOT_THREAD.start()
    return "Blue autopilot ON. It is now running in background, so you can keep typing commands in VS Code terminal."
