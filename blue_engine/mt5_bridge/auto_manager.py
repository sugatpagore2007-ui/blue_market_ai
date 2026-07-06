"""
Auto Manager for Blue Market AI MT5 trades.

What it does:
- moves SL to breakeven at 1R
- partial closes at TP1
- trails SL after TP1
- closes trade if opposite signal appears
- respects daily loss guard
- supports autonomous all-pairs monitoring

It is terminal-only: it never opens or pops up MT5. Keep MT5 open manually.
"""
from __future__ import annotations

import json
import os
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:
    mt5 = None

from config import (
    MT5_COMMENT,
    MT5_MAGIC_NUMBER,
    MT5_DEFAULT_DEVIATION,
    AUTO_TRADE_PLANS_FILE,
    AUTO_MANAGER_ENABLED,
    AUTO_MANAGER_DEMO_ONLY,
    AUTO_MANAGER_ALLOW_REAL_ACCOUNT,
    AUTO_MANAGER_CHECK_SECONDS,
    AUTO_MANAGER_BREAKEVEN_AT_R,
    AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1,
    AUTO_MANAGER_PARTIAL_CLOSE_PERCENT,
    AUTO_MANAGER_TRAIL_AFTER_TP1,
    AUTO_MANAGER_TRAIL_LOCK_R,
    AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL,
    AUTO_MANAGER_MANAGE_ONLY_BLUE_TRADES,
    MAX_DAILY_LOSS_PERCENT,
    PYRAMIDING_ENABLED,
    PYRAMID_MAX_LEVELS,
    PYRAMID_ADD_AT_R,
    PYRAMID_LOT_MULTIPLIERS,
    PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R,
    PYRAMID_MIN_CONFIDENCE,
    PYRAMID_REQUIRE_BREAKEVEN,
    PYRAMID_COOLDOWN_SECONDS,
    PYRAMID_USE_EXISTING_TP,
    PYRAMID_COMMENT_SUFFIX,
)
from .terminal import ensure_connected, modify_position, close_position, map_symbol
from analysis.signal_engine import build_signal
from utils.symbols import resolve_symbol


_MANAGER_STATE_FILE = "auto_manager_state.json"
_MANAGER_THREAD = None
_MANAGER_THREAD_LOCK = threading.Lock()
_MANAGER_RUN_STATE_FILE = "auto_manager_background_state.json"


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def save_auto_trade_plan(signal: Dict[str, Any], order_result: Any = None, symbol: str = "") -> None:
    """Save TP1/TP2/entry/SL plan locally so manager can handle partial close and trailing."""
    plans = _load_json(AUTO_TRADE_PLANS_FILE, {})
    ticket = None
    for attr in ["order", "deal"]:
        try:
            v = getattr(order_result, attr, None)
            if v:
                ticket = str(v)
                break
        except Exception:
            pass
    key = ticket or f"{symbol or signal.get('symbol','UNKNOWN')}_{int(time.time())}"
    plans[key] = {
        "ticket": ticket,
        "symbol": symbol or signal.get("symbol"),
        "ticker": signal.get("ticker"),
        "action": signal.get("action"),
        "entry": signal.get("entry"),
        "stop_loss": signal.get("stop_loss"),
        "original_entry": signal.get("original_entry", signal.get("entry")),
        "original_stop_loss": signal.get("original_stop_loss", signal.get("stop_loss")),
        "pyramid_child": signal.get("pyramid_child", False),
        "pyramid_level": signal.get("pyramid_level", 0),
        "target_1": signal.get("target_1"),
        "target_2": signal.get("target_2"),
        "confidence": signal.get("confidence"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_json(AUTO_TRADE_PLANS_FILE, plans)


def _find_plan_for_position(p) -> Dict[str, Any]:
    plans = _load_json(AUTO_TRADE_PLANS_FILE, {})
    # exact ticket first
    if str(p.ticket) in plans:
        return plans[str(p.ticket)]
    # fallback: latest same symbol/action
    side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
    same = [v for v in plans.values() if str(v.get("symbol", "")).upper() == str(p.symbol).upper() and str(v.get("action", "")).upper() == side]
    if same:
        # For an original position, prefer the original/main plan over pyramid-child plans.
        # This keeps level 2 pyramiding from being blocked just because level 1 was saved later.
        main = [v for v in same if not bool(v.get("pyramid_child"))]
        use = main or same
        use.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return use[0]
    return {}


def _state() -> Dict[str, Any]:
    return _load_json(_MANAGER_STATE_FILE, {})


def _save_state(st: Dict[str, Any]) -> None:
    _save_json(_MANAGER_STATE_FILE, st)


def _account_is_demo() -> bool:
    if mt5 is None:
        return False
    acc = mt5.account_info()
    if acc is None:
        return False
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    return demo_const is not None and getattr(acc, "trade_mode", None) == demo_const


def _daily_loss_guard_ok() -> Dict[str, Any]:
    if mt5 is None:
        return {"ok": False, "message": "MetaTrader5 package missing."}
    acc = mt5.account_info()
    if acc is None:
        return {"ok": False, "message": "No MT5 account info."}
    from datetime import timedelta
    start = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    deals = mt5.history_deals_get(start, datetime.now()) or []
    blue_deals = [d for d in deals if str(getattr(d, "comment", "")).startswith(MT5_COMMENT)]
    profit = sum(float(getattr(d, "profit", 0.0)) for d in blue_deals)
    limit = -abs(float(acc.balance) * float(MAX_DAILY_LOSS_PERCENT) / 100.0)
    if profit <= limit:
        return {"ok": False, "message": f"Daily loss guard active. Today Blue P/L {round(profit,2)} <= {round(limit,2)}."}
    return {"ok": True, "message": f"Daily loss guard OK. Today Blue P/L {round(profit,2)}."}


def auto_manager_status() -> str:
    return (
        "Auto Manager Status\n"
        f"AUTO_MANAGER_ENABLED             : {AUTO_MANAGER_ENABLED}\n"
        f"AUTO_MANAGER_DEMO_ONLY           : {AUTO_MANAGER_DEMO_ONLY}\n"
        f"AUTO_MANAGER_BREAKEVEN_AT_R      : {AUTO_MANAGER_BREAKEVEN_AT_R}R\n"
        f"AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1: {AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1}\n"
        f"AUTO_MANAGER_PARTIAL_CLOSE_PERCENT: {AUTO_MANAGER_PARTIAL_CLOSE_PERCENT}%\n"
        f"AUTO_MANAGER_TRAIL_AFTER_TP1     : {AUTO_MANAGER_TRAIL_AFTER_TP1}\n"
        f"AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL: {AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL}\n"
        f"AUTO_MANAGER_CHECK_SECONDS       : {AUTO_MANAGER_CHECK_SECONDS}\n"
        f"PYRAMIDING_ENABLED               : {_pyramiding_enabled_now()}\n"
        f"PYRAMID_MAX_LEVELS               : {PYRAMID_MAX_LEVELS}\n"
        f"PYRAMID_MAX_DISTANCE_ORIGINAL_R  : {PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R}"
    )


def _current_price(p) -> Optional[float]:
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return None
    return float(tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask)


def _profit_r(p, price: float) -> float:
    entry = float(p.price_open)
    sl = float(p.sl or 0)
    if sl <= 0:
        return 0.0
    risk = abs(entry - sl)
    if risk <= 0:
        return 0.0
    if p.type == mt5.POSITION_TYPE_BUY:
        return (price - entry) / risk
    return (entry - price) / risk


def _tp1_from_plan_or_r(p, plan: Dict[str, Any]) -> float:
    try:
        tp1 = float(plan.get("target_1") or 0)
        if tp1 > 0:
            return tp1
    except Exception:
        pass
    entry = float(p.price_open)
    sl = float(p.sl or 0)
    risk = abs(entry - sl)
    if p.type == mt5.POSITION_TYPE_BUY:
        return entry + risk
    return entry - risk


def _is_tp1_hit(p, price: float, tp1: float) -> bool:
    if p.type == mt5.POSITION_TYPE_BUY:
        return price >= tp1
    return price <= tp1


def _opposite_signal_exists(p, plan: Dict[str, Any]) -> Optional[str]:
    if not AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL:
        return None
    symbol_text = str(plan.get("ticker") or plan.get("symbol") or p.symbol)
    # Convert MT5 symbol back to a common supported alias where possible.
    name, ticker = resolve_symbol(symbol_text.lower())
    if not ticker:
        name, ticker = p.symbol, symbol_text
    try:
        r = build_signal(name, ticker, account=None)
    except Exception:
        return None
    current_side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
    new_side = str(r.get("action", "WAIT")).upper()
    confidence = float(r.get("confidence", 0))
    if new_side in ["BUY", "SELL"] and new_side != current_side and confidence >= 70:
        return f"Opposite {new_side} signal appeared with {confidence}% confidence."
    return None



def _pyramid_runtime_state() -> Dict[str, Any]:
    st = _state()
    return st.setdefault("pyramiding", {})


def _pyramiding_enabled_now() -> bool:
    pyr = _pyramid_runtime_state()
    if "enabled" in pyr:
        return bool(pyr.get("enabled"))
    return bool(PYRAMIDING_ENABLED)


def set_pyramiding_enabled(enabled: bool) -> str:
    st = _state()
    st.setdefault("pyramiding", {})["enabled"] = bool(enabled)
    st["pyramiding"]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_state(st)
    return "Pyramiding ON." if enabled else "Pyramiding OFF."


def pyramiding_status() -> str:
    enabled = _pyramiding_enabled_now()
    return (
        "Pyramiding Status\n"
        f"Enabled                         : {enabled}\n"
        f"Max levels                      : {PYRAMID_MAX_LEVELS}\n"
        f"Add at R                        : {PYRAMID_ADD_AT_R}\n"
        f"Lot multipliers                 : {PYRAMID_LOT_MULTIPLIERS}\n"
        f"Max distance from original entry: {PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R}R\n"
        f"Min confidence                  : {PYRAMID_MIN_CONFIDENCE}%\n"
        f"Require breakeven first         : {PYRAMID_REQUIRE_BREAKEVEN}\n"
        f"Cooldown seconds                : {PYRAMID_COOLDOWN_SECONDS}"
    )


def _round_volume_for_symbol(symbol: str, volume: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return round(float(volume), 2)
    step = float(getattr(info, "volume_step", 0.01) or 0.01)
    min_v = float(getattr(info, "volume_min", step) or step)
    max_v = float(getattr(info, "volume_max", volume) or volume)
    if step <= 0:
        step = 0.01
    import math
    rounded = math.floor(float(volume) / step) * step
    rounded = max(min_v, min(rounded, max_v))
    decimals = max(0, min(8, len(str(step).split(".")[-1]) if "." in str(step) else 0))
    return round(rounded, decimals)


def _normalize_price(symbol: str, price: float) -> float:
    info = mt5.symbol_info(symbol)
    digits = int(getattr(info, "digits", 5) or 5) if info else 5
    return round(float(price), digits)


def _send_pyramid_order(p, level: int, volume: float, price: float, sl: float, tp: float) -> Any:
    side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": p.symbol,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": MT5_DEFAULT_DEVIATION,
        "magic": MT5_MAGIC_NUMBER,
        "comment": f"{MT5_COMMENT}{PYRAMID_COMMENT_SUFFIX}{level}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    # filling fallback for Exness symbols
    last = None
    for mode_name in ["ORDER_FILLING_IOC", "ORDER_FILLING_FOK", "ORDER_FILLING_RETURN"]:
        mode = getattr(mt5, mode_name, None)
        if mode is None:
            continue
        req = dict(request)
        req["type_filling"] = mode
        last = mt5.order_send(req)
        ret = getattr(last, "retcode", None)
        if ret in [getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)]:
            return last
    return last


def _maybe_pyramid_position(p, price: float, r_now: float, plan: Dict[str, Any], pos_state: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    if not _pyramiding_enabled_now():
        return lines
    if bool(plan.get("pyramid_child")):
        return lines
    max_levels = int(PYRAMID_MAX_LEVELS)
    if max_levels <= 0:
        return lines
    done_levels = int(pos_state.get("pyramid_levels_done", 0) or 0)
    if done_levels >= max_levels:
        return lines
    if PYRAMID_REQUIRE_BREAKEVEN and not pos_state.get("breakeven_done"):
        lines.append("  Pyramiding blocked: waiting for breakeven protection first.")
        return lines
    now = time.time()
    last_time = float(pos_state.get("last_pyramid_time", 0) or 0)
    if last_time and now - last_time < float(PYRAMID_COOLDOWN_SECONDS):
        return lines

    original_entry = float(plan.get("original_entry") or plan.get("entry") or p.price_open)
    original_sl = float(plan.get("original_stop_loss") or plan.get("stop_loss") or p.sl or p.price_open)
    original_risk = abs(original_entry - original_sl)
    if original_risk <= 0:
        lines.append("  Pyramiding blocked: missing original risk distance.")
        return lines
    distance_r = abs(float(price) - original_entry) / original_risk
    if distance_r > float(PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R):
        lines.append(f"  Pyramiding blocked: price is {round(distance_r,2)}R from original entry, max allowed {PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R}R. Not chasing.")
        return lines

    next_level = done_levels + 1
    add_levels = list(PYRAMID_ADD_AT_R)
    threshold = float(add_levels[min(done_levels, len(add_levels)-1)] if add_levels else 1.0)
    if r_now < threshold:
        return lines

    # Confirm fresh signal still agrees before adding.
    symbol_text = str(plan.get("ticker") or plan.get("symbol") or p.symbol)
    name, ticker = resolve_symbol(symbol_text.lower())
    if not ticker:
        name, ticker = p.symbol, symbol_text
    try:
        sig = build_signal(name, ticker, account=None)
        fresh_action = str(sig.get("action", "WAIT")).upper()
        fresh_conf = float(sig.get("confidence", 0))
    except Exception as e:
        lines.append(f"  Pyramiding blocked: fresh signal check failed: {e}")
        return lines
    current_side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
    if fresh_action != current_side or fresh_conf < float(PYRAMID_MIN_CONFIDENCE):
        lines.append(f"  Pyramiding blocked: fresh signal {fresh_action} {fresh_conf}% does not confirm {current_side} >= {PYRAMID_MIN_CONFIDENCE}%.")
        return lines

    multipliers = list(PYRAMID_LOT_MULTIPLIERS)
    multiplier = float(multipliers[min(done_levels, len(multipliers)-1)] if multipliers else 0.5)
    volume = _round_volume_for_symbol(p.symbol, float(p.volume) * multiplier)
    if volume <= 0:
        lines.append("  Pyramiding blocked: calculated added lot is zero.")
        return lines
    info = mt5.symbol_info(p.symbol)
    min_vol = float(getattr(info, "volume_min", 0.01) or 0.01) if info else 0.01
    if volume < min_vol:
        lines.append(f"  Pyramiding blocked: added lot {volume} is below minimum {min_vol}.")
        return lines

    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        lines.append("  Pyramiding blocked: no live tick.")
        return lines
    entry_price = float(tick.ask if current_side == "BUY" else tick.bid)
    # The added position should be protected by original entry/breakeven, not a wide fresh SL.
    protected_sl = float(p.sl or original_entry)
    if current_side == "BUY":
        sl = max(protected_sl, original_entry) if PYRAMID_REQUIRE_BREAKEVEN else protected_sl
        if sl >= entry_price:
            sl = original_entry
    else:
        sl = min(protected_sl, original_entry) if PYRAMID_REQUIRE_BREAKEVEN else protected_sl
        if sl <= entry_price:
            sl = original_entry
    tp = float(p.tp or plan.get("target_2") or plan.get("target_1") or 0)
    if tp <= 0 or not PYRAMID_USE_EXISTING_TP:
        # fallback: aim from current entry using remaining original risk
        if current_side == "BUY":
            tp = entry_price + original_risk
        else:
            tp = entry_price - original_risk
    entry_price = _normalize_price(p.symbol, entry_price)
    sl = _normalize_price(p.symbol, sl)
    tp = _normalize_price(p.symbol, tp)
    if current_side == "BUY" and not (sl < entry_price < tp):
        lines.append(f"  Pyramiding blocked: invalid BUY levels SL {sl}, entry {entry_price}, TP {tp}.")
        return lines
    if current_side == "SELL" and not (tp < entry_price < sl):
        lines.append(f"  Pyramiding blocked: invalid SELL levels TP {tp}, entry {entry_price}, SL {sl}.")
        return lines

    result = _send_pyramid_order(p, next_level, volume, entry_price, sl, tp)
    ret = getattr(result, "retcode", None)
    success = ret in [getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)]
    if success:
        pos_state["pyramid_levels_done"] = next_level
        pos_state["last_pyramid_time"] = now
        child_signal = {
            "symbol": p.symbol, "ticker": plan.get("ticker") or p.symbol, "action": current_side,
            "entry": entry_price, "stop_loss": sl, "target_1": plan.get("target_1") or tp, "target_2": tp,
            "confidence": fresh_conf, "original_entry": original_entry, "original_stop_loss": original_sl,
            "pyramid_child": True, "pyramid_level": next_level,
        }
        save_auto_trade_plan(child_signal, result, p.symbol)
        lines.append(f"  PYRAMID LEVEL {next_level} ADDED: {current_side} {volume} lots at {entry_price}, SL {sl}, TP {tp}. Distance from original: {round(distance_r,2)}R.")
    else:
        lines.append(f"  Pyramiding order failed. Retcode {ret}. Result: {result}")
    return lines

def manage_once() -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    if AUTO_MANAGER_DEMO_ONLY and not _account_is_demo() and not AUTO_MANAGER_ALLOW_REAL_ACCOUNT:
        return "Auto manager blocked: MT5 account is not demo. Keep demo-only protection on while testing."
    guard = _daily_loss_guard_ok()
    if not guard.get("ok"):
        return guard.get("message", "Daily loss guard active.")
    positions = mt5.positions_get()
    if positions is None:
        return "Could not read MT5 positions."
    if len(positions) == 0:
        return "Auto manager: no open positions."

    st = _state()
    lines: List[str] = ["Auto manager scan"]
    managed_count = 0
    for p in positions:
        if AUTO_MANAGER_MANAGE_ONLY_BLUE_TRADES:
            comment = str(getattr(p, "comment", ""))
            magic = int(getattr(p, "magic", 0) or 0)
            if not comment.startswith(MT5_COMMENT) and magic != MT5_MAGIC_NUMBER:
                continue
        managed_count += 1
        key = str(p.ticket)
        pos_state = st.setdefault(key, {})
        price = _current_price(p)
        if price is None:
            lines.append(f"#{p.ticket} {p.symbol}: no live tick.")
            continue
        r_now = _profit_r(p, price)
        plan = _find_plan_for_position(p)
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        lines.append(f"#{p.ticket} {p.symbol} {side}: current R = {round(r_now,2)}")

        # Close on opposite signal.
        opp = _opposite_signal_exists(p, plan)
        if opp:
            lines.append(f"  Opposite signal: {opp}")
            lines.append("  " + close_position(int(p.ticket), confirm=False))
            pos_state["closed_by_opposite"] = True
            continue

        # Move SL to breakeven at 1R.
        if r_now >= float(AUTO_MANAGER_BREAKEVEN_AT_R) and not pos_state.get("breakeven_done"):
            be_sl = float(p.price_open)
            lines.append(f"  Moving SL to breakeven at {be_sl}.")
            lines.append("  " + modify_position(int(p.ticket), sl=be_sl, tp=float(p.tp or 0), confirm=False))
            pos_state["breakeven_done"] = True

        # Partial close at TP1.
        tp1 = _tp1_from_plan_or_r(p, plan)
        if AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1 and _is_tp1_hit(p, price, tp1) and not pos_state.get("tp1_partial_done"):
            close_percent = max(1.0, min(float(AUTO_MANAGER_PARTIAL_CLOSE_PERCENT), 100.0))
            volume = float(p.volume) * close_percent / 100.0
            info = mt5.symbol_info(p.symbol)
            step = float(getattr(info, "volume_step", 0.01) or 0.01) if info else 0.01
            min_vol = float(getattr(info, "volume_min", step) or step) if info else step
            volume = max(min_vol, round((volume // step) * step, 8))
            if volume < float(p.volume):
                lines.append(f"  TP1 hit near {tp1}. Partial closing {volume} lots.")
                lines.append("  " + close_position(int(p.ticket), partial_volume=volume, confirm=False))
                pos_state["tp1_partial_done"] = True
            else:
                lines.append("  TP1 hit, but position too small for safe partial close.")
                pos_state["tp1_partial_done"] = True

        # Trail after TP1.
        if AUTO_MANAGER_TRAIL_AFTER_TP1 and (pos_state.get("tp1_partial_done") or _is_tp1_hit(p, price, tp1)):
            entry = float(p.price_open)
            risk = abs(entry - float(p.sl or entry))
            if risk > 0:
                if p.type == mt5.POSITION_TYPE_BUY:
                    new_sl = max(float(p.sl or 0), entry + risk * float(AUTO_MANAGER_TRAIL_LOCK_R))
                    if new_sl < price:
                        lines.append(f"  Trailing SL after TP1 to {round(new_sl, 5)}.")
                        lines.append("  " + modify_position(int(p.ticket), sl=new_sl, tp=float(p.tp or 0), confirm=False))
                else:
                    old_sl = float(p.sl or 10**9)
                    new_sl = min(old_sl, entry - risk * float(AUTO_MANAGER_TRAIL_LOCK_R))
                    if new_sl > price:
                        lines.append(f"  Trailing SL after TP1 to {round(new_sl, 5)}.")
                        lines.append("  " + modify_position(int(p.ticket), sl=new_sl, tp=float(p.tp or 0), confirm=False))
    _save_state(st)
    if managed_count == 0:
        lines.append("No Blue-managed open positions found.")
    return "\n".join(lines)



def _manager_run_state() -> Dict[str, Any]:
    return _load_json(_MANAGER_RUN_STATE_FILE, {"enabled": False, "updated_at": None})


def _save_manager_run_state(enabled: bool) -> None:
    _save_json(_MANAGER_RUN_STATE_FILE, {"enabled": bool(enabled), "updated_at": datetime.now().isoformat(timespec="seconds")})


def _manager_thread_alive() -> bool:
    global _MANAGER_THREAD
    return _MANAGER_THREAD is not None and _MANAGER_THREAD.is_alive()


def _manager_background_loop(seconds: Optional[int] = None) -> None:
    seconds = int(seconds or AUTO_MANAGER_CHECK_SECONDS)
    print("\n[AUTO MANAGER] Always-active background manager started.", flush=True)
    while _manager_run_state().get("enabled"):
        try:
            msg = manage_once()
            # Keep terminal clean: only print important actions or a short heartbeat.
            important = any(x in msg.lower() for x in ["moving sl", "partial closing", "trailing sl", "opposite signal", "blocked", "error", "could not"])
            if important:
                print("\n" + "=" * 72, flush=True)
                print("AUTO MANAGER ACTION", flush=True)
                print("=" * 72, flush=True)
                print(msg, flush=True)
                print("=" * 72 + "\n", flush=True)
        except Exception as exc:
            print(f"\n[AUTO MANAGER ERROR] {exc}\n", flush=True)
        time.sleep(max(5, seconds))
    print("[AUTO MANAGER] Background manager stopped.", flush=True)


def start_auto_manager_background(seconds: Optional[int] = None) -> str:
    """Start continuous trade management without blocking the terminal."""
    global _MANAGER_THREAD
    if not AUTO_MANAGER_ENABLED:
        return "Auto manager background not started: AUTO_MANAGER_ENABLED is False."
    with _MANAGER_THREAD_LOCK:
        if _manager_thread_alive() and _manager_run_state().get("enabled"):
            return "Auto manager is already running in background."
        _save_manager_run_state(True)
        _MANAGER_THREAD = threading.Thread(
            target=_manager_background_loop,
            kwargs={"seconds": seconds or AUTO_MANAGER_CHECK_SECONDS},
            daemon=True,
            name="BlueAutoManagerThread",
        )
        _MANAGER_THREAD.start()
    return "Auto manager background ON. Blue will manage open trades automatically while terminal commands stay usable."


def stop_auto_manager_background() -> str:
    _save_manager_run_state(False)
    return "Auto manager background OFF."


def auto_manager_background_status() -> str:
    st = _manager_run_state()
    return (
        "Auto Manager Background Status\n"
        f"State              : {'ON' if st.get('enabled') else 'OFF'}\n"
        f"Thread active      : {'YES' if _manager_thread_alive() else 'NO'}\n"
        f"Check seconds      : {AUTO_MANAGER_CHECK_SECONDS}\n"
        f"Updated at         : {st.get('updated_at')}\n"
        "Meaning            : after autopilot punches a trade, Blue manages BE/partial/trailing automatically."
    )

def manager_loop(cycles: int = 10, seconds: Optional[int] = None) -> str:
    seconds = int(seconds or AUTO_MANAGER_CHECK_SECONDS)
    print("Auto manager loop started. Press Ctrl+C to stop.")
    last = ""
    for i in range(int(cycles)):
        last = manage_once()
        print(last)
        if i < int(cycles) - 1:
            time.sleep(max(5, seconds))
    return "Auto manager loop finished."
