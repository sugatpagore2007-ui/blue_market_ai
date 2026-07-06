"""Phase 15.15 — Order Execution Doctor.

Read-only diagnostics for why Blue/MT5 did not punch an order.
This module never sends an order. It can optionally run MT5 order_check(),
which is a broker validation dry-run, but it does not call order_send().
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:
    mt5 = None

try:
    import config
except Exception:  # pragma: no cover
    config = None

from .terminal import ensure_connected, select_symbol, resolve_mt5_symbol, map_symbol, lot_size_from_broker


def _get(name: str, default: Any = None) -> Any:
    return getattr(config, name, default) if config is not None else default


def _yesno(v: Any) -> str:
    if v is True:
        return "OK"
    if v is False:
        return "FAIL"
    return str(v)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _account_is_demo_like(acc: Any) -> Tuple[bool, str]:
    if mt5 is None or acc is None:
        return False, "no account"
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_const is not None and getattr(acc, "trade_mode", None) == demo_const:
        return True, "MT5 trade_mode=DEMO"
    keywords = _get("AUTO_TRADE_DEMO_SERVER_KEYWORDS", ["demo", "trial", "practice"])
    blob = " ".join([
        str(getattr(acc, "server", "") or ""),
        str(getattr(acc, "name", "") or ""),
        str(getattr(acc, "company", "") or ""),
    ]).lower()
    matched = [k for k in keywords if str(k).lower() in blob]
    if matched:
        return True, "server/name/company contains " + ", ".join(map(str, matched))
    return False, "not detected as demo/trial"


def _max_spread_for_symbol(symbol: str) -> float:
    base_limit = float(_get("MAX_SPREAD_POINTS", 80) or 80)
    by_symbol = _get("MAX_SPREAD_POINTS_BY_SYMBOL", {}) or {}
    name = (symbol or "").upper()
    if name in by_symbol:
        return float(by_symbol[name])
    base = name[:-1] if name.endswith("M") else name
    if base in by_symbol:
        return float(by_symbol[base])
    for k, v in by_symbol.items():
        kk = str(k).upper()
        if name.startswith(kk) or kk.startswith(base):
            return float(v)
    return base_limit


def _today_blue_entry_count_and_profit() -> Dict[str, Any]:
    if mt5 is None:
        return {"entry_count": 0, "profit": 0.0, "deals": 0, "ok": False}
    try:
        end = datetime.now()
        start = datetime(end.year, end.month, end.day)
        deals = mt5.history_deals_get(start, end) or []
    except Exception as exc:
        return {"entry_count": 0, "profit": 0.0, "deals": 0, "ok": False, "error": str(exc)}
    magic = int(_get("MT5_MAGIC_NUMBER", 260530) or 260530)
    comment_prefix = str(_get("MT5_COMMENT", "BlueMarketAI") or "BlueMarketAI")
    entry_in = getattr(mt5, "DEAL_ENTRY_IN", None)
    entry_count = 0
    blue_deals = []
    for d in deals:
        is_blue = int(getattr(d, "magic", 0) or 0) == magic or str(getattr(d, "comment", "") or "").startswith(comment_prefix)
        if not is_blue:
            continue
        blue_deals.append(d)
        if entry_in is None or getattr(d, "entry", None) == entry_in:
            entry_count += 1
    profit = sum(_safe_float(getattr(d, "profit", 0.0), 0.0) for d in blue_deals)
    return {"entry_count": entry_count, "profit": profit, "deals": len(blue_deals), "ok": True}


def _signal_summary(signal: Optional[Dict[str, Any]]) -> Tuple[str, str, float, str]:
    if not signal:
        return "UNKNOWN", "WAIT", 0.0, "unknown"
    symbol = str(signal.get("symbol") or signal.get("ticker") or "UNKNOWN")
    action = str(signal.get("action") or "WAIT").upper()
    confidence = _safe_float(signal.get("confidence"), 0.0)
    grade = "unknown"
    grades = signal.get("trade_quality_grades") or {}
    if isinstance(grades, dict):
        grade = str(grades.get("overall") or grades.get("setup") or "unknown")
    auto_filter = signal.get("a_plus_filter") or {}
    if isinstance(auto_filter, dict) and auto_filter.get("grade"):
        grade = str(auto_filter.get("grade"))
    return symbol, action, confidence, grade


def _make_dry_request(symbol: str, signal: Optional[Dict[str, Any]], action_override: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Build a market-order dry-run request for mt5.order_check(). No order_send."""
    notes: List[str] = []
    if mt5 is None:
        return None, ["MetaTrader5 package missing."]
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    acc = mt5.account_info()
    if tick is None or info is None or acc is None:
        return None, ["Missing tick/symbol/account info."]
    _sym, sig_action, _conf, _grade = _signal_summary(signal)
    action = (action_override or sig_action or "BUY").upper()
    if action not in ["BUY", "SELL"]:
        notes.append("Signal is WAIT, so dry-run uses BUY only to test broker mechanics.")
        action = "BUY"
    price = float(tick.ask if action == "BUY" else tick.bid)
    # Use a conservative minimum stop distance if there is no signal.
    point = float(getattr(info, "point", 0.0) or 0.0)
    stops = float(getattr(info, "trade_stops_level", 0.0) or 0.0)
    freeze = float(getattr(info, "trade_freeze_level", 0.0) or 0.0)
    min_dist = max(stops, freeze, 10.0) * point if point else abs(price) * 0.001
    if signal:
        sig_entry = _safe_float(signal.get("entry"), price)
        sig_sl = _safe_float(signal.get("stop_loss"), price)
        sig_tp = _safe_float(signal.get("target_1") or signal.get("target_2"), price)
        risk = abs(sig_entry - sig_sl)
        rr = abs(sig_tp - sig_entry) / risk if risk > 0 else 2.0
        risk = max(risk, min_dist * 3)
        rr = max(1.0, min(4.0, rr))
    else:
        risk = max(min_dist * 4, abs(price) * 0.002)
        rr = 2.0
    digits = int(getattr(info, "digits", 5) or 5)
    if action == "BUY":
        sl = round(price - risk, digits)
        tp = round(price + risk * rr, digits)
        order_type = mt5.ORDER_TYPE_BUY
    else:
        sl = round(price + risk, digits)
        tp = round(price - risk * rr, digits)
        order_type = mt5.ORDER_TYPE_SELL
    lot = lot_size_from_broker(symbol, float(getattr(acc, "balance", 0.0) or 0.0), float(_get("AUTO_TRADE_RISK_PERCENT", 1.0) or 1.0), price, sl)
    volume = float(lot.get("recommended_lot_size", 0.0) or 0.0) if lot.get("ok") else float(getattr(info, "volume_min", 0.01) or 0.01)
    if volume <= 0:
        volume = float(getattr(info, "volume_min", 0.01) or 0.01)
        notes.append("Lot calculation returned zero, dry-run uses broker minimum volume.")
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": int(_get("MT5_DEFAULT_DEVIATION", 20) or 20),
        "magic": int(_get("MT5_MAGIC_NUMBER", 260530) or 260530),
        "comment": str(_get("MT5_COMMENT", "BlueMarketAI")) + " DOCTOR CHECK",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 1),
    }
    return request, notes


def order_doctor_report(symbol_text: str = "gold", signal: Optional[Dict[str, Any]] = None, action_override: Optional[str] = None, run_order_check: bool = True) -> str:
    """Return a clear read-only report explaining if Blue can punch an MT5 order."""
    lines: List[str] = []
    blockers: List[str] = []
    warnings: List[str] = []
    lines.append("ORDER EXECUTION DOCTOR")
    lines.append("=" * 72)
    lines.append("Mode: READ-ONLY diagnosis. No order_send() is called.")

    # Config checks
    auto_exec = bool(_get("AUTO_ORDER_EXECUTION", False))
    stage2 = bool(_get("MT5_STAGE2_EXECUTION_ENABLED", False))
    demo_only = bool(_get("AUTO_TRADE_DEMO_ONLY", True))
    allow_real = bool(_get("AUTO_TRADE_ALLOW_REAL_ACCOUNT", False))
    min_conf = float(_get("MIN_AUTO_TRADE_CONFIDENCE", 80) or 80)
    max_trades = int(_get("MAX_AUTO_TRADES_PER_DAY", 4) or 4)
    max_loss_pct = float(_get("MAX_DAILY_LOSS_PERCENT", 2.0) or 2.0)
    lines.append("\nCONFIG / SAFETY")
    lines.append(f"AUTO_ORDER_EXECUTION        : {_yesno(auto_exec)}")
    lines.append(f"MT5_STAGE2_EXECUTION_ENABLED: {_yesno(stage2)}")
    lines.append(f"AUTO_TRADE_DEMO_ONLY        : {demo_only}")
    lines.append(f"AUTO_TRADE_ALLOW_REAL       : {allow_real}")
    lines.append(f"MIN_AUTO_TRADE_CONFIDENCE   : {min_conf}%")
    if not auto_exec:
        blockers.append("AUTO_ORDER_EXECUTION is OFF in config.py")
    if not stage2:
        blockers.append("MT5_STAGE2_EXECUTION_ENABLED is OFF in config.py")

    # Signal checks
    sig_symbol, sig_action, confidence, grade = _signal_summary(signal)
    if signal:
        lines.append("\nSIGNAL CHECK")
        lines.append(f"Signal symbol : {sig_symbol}")
        lines.append(f"Action        : {sig_action}")
        lines.append(f"Confidence    : {confidence}%")
        lines.append(f"Grade         : {grade}")
        if sig_action not in ["BUY", "SELL"]:
            blockers.append("Signal is WAIT/no-trade")
        if confidence < min_conf:
            blockers.append(f"Signal confidence {confidence}% is below minimum {min_conf}%")
    else:
        lines.append("\nSIGNAL CHECK")
        lines.append("No live signal supplied. Doctor will test broker/order mechanics only.")

    # MT5 package/connection
    lines.append("\nMT5 CONNECTION")
    if mt5 is None:
        lines.append("MetaTrader5 package: FAIL / missing")
        blockers.append("MetaTrader5 Python package is not installed")
        return _finish(lines, blockers, warnings)
    ok, msg = ensure_connected()
    lines.append(f"Connect result : {'OK' if ok else 'FAIL'} — {msg}")
    if not ok:
        blockers.append("MT5 is not connected/open/logged in")
        return _finish(lines, blockers, warnings)

    acc = mt5.account_info()
    term = mt5.terminal_info()
    if acc is None:
        blockers.append("MT5 account_info() is unavailable")
    else:
        is_demo, demo_reason = _account_is_demo_like(acc)
        lines.append(f"Account       : {getattr(acc, 'login', '')} | {getattr(acc, 'server', '')}")
        lines.append(f"Balance/equity: {round(_safe_float(getattr(acc, 'balance', 0)),2)} / {round(_safe_float(getattr(acc, 'equity', 0)),2)} {getattr(acc, 'currency', '')}")
        lines.append(f"Demo detected : {'OK' if is_demo else 'NO'} — {demo_reason}")
        lines.append(f"Account trade : allowed={getattr(acc, 'trade_allowed', 'unknown')} expert={getattr(acc, 'trade_expert', 'unknown')}")
        if demo_only and not is_demo and not allow_real:
            blockers.append("Demo-only guard blocks this account because it is not detected as demo/trial")
        if getattr(acc, "trade_allowed", True) is False:
            blockers.append("Account trading is not allowed by MT5/broker")
        if getattr(acc, "trade_expert", True) is False:
            warnings.append("MT5 account reports expert trading disabled")
    if term is not None:
        lines.append(f"Terminal      : connected={getattr(term, 'connected', 'unknown')} trade_allowed={getattr(term, 'trade_allowed', 'unknown')}")
        if getattr(term, "trade_allowed", True) is False:
            blockers.append("Terminal Algo Trading is OFF / trading not allowed")

    # Symbol checks
    lines.append("\nSYMBOL / MARKET")
    raw_symbol = symbol_text or (signal.get("ticker") if signal else "gold") or "gold"
    preferred = map_symbol(raw_symbol)
    resolved = resolve_mt5_symbol(raw_symbol) or preferred
    ok_sel, selected = select_symbol(raw_symbol)
    lines.append(f"Requested     : {raw_symbol}")
    lines.append(f"Mapped        : {preferred}")
    lines.append(f"Resolved      : {resolved}")
    lines.append(f"Selected      : {'OK' if ok_sel else 'FAIL'} — {selected}")
    if not ok_sel:
        blockers.append(f"Broker symbol could not be selected: {selected}")
        return _finish(lines, blockers, warnings)
    info = mt5.symbol_info(selected)
    tick = mt5.symbol_info_tick(selected)
    if info is None:
        blockers.append(f"symbol_info unavailable for {selected}")
    if tick is None:
        blockers.append(f"No live bid/ask tick for {selected}")
    if info is not None:
        spread = float(getattr(info, "spread", 0) or 0)
        spread_limit = _max_spread_for_symbol(selected)
        lines.append(f"Trade mode    : {getattr(info, 'trade_mode', 'unknown')}")
        lines.append(f"Spread        : {spread} points / limit {spread_limit}")
        lines.append(f"Stops/freeze  : {getattr(info, 'trade_stops_level', 'unknown')} / {getattr(info, 'trade_freeze_level', 'unknown')} points")
        lines.append(f"Volume min/step/max: {getattr(info, 'volume_min', 'unknown')} / {getattr(info, 'volume_step', 'unknown')} / {getattr(info, 'volume_max', 'unknown')}")
        lines.append(f"Filling mode  : {getattr(info, 'filling_mode', 'unknown')} | Order mode: {getattr(info, 'order_mode', 'unknown')}")
        if spread > spread_limit:
            blockers.append(f"Spread too high: {spread} points > {spread_limit}")
        if getattr(info, "visible", True) is False:
            warnings.append("Symbol is not visible in Market Watch")
    if tick is not None:
        lines.append(f"Bid/Ask       : {getattr(tick, 'bid', None)} / {getattr(tick, 'ask', None)}")

    # Daily guard and existing position checks.
    if acc is not None:
        day = _today_blue_entry_count_and_profit()
        lines.append("\nDAILY GUARDS")
        lines.append(f"Blue entries today: {day.get('entry_count')} / max {max_trades}")
        lines.append(f"Blue P/L today   : {round(_safe_float(day.get('profit')),2)} | loss limit {round(-abs(_safe_float(getattr(acc, 'balance', 0))*max_loss_pct/100.0),2)}")
        if int(day.get("entry_count", 0) or 0) >= max_trades:
            blockers.append("Daily auto trade limit reached")
        if _safe_float(day.get("profit"), 0.0) <= -abs(_safe_float(getattr(acc, "balance", 0.0), 0.0) * max_loss_pct / 100.0):
            blockers.append("Daily loss guard is active")
    try:
        positions = mt5.positions_get(symbol=selected) or []
        blue_magic = int(_get("MT5_MAGIC_NUMBER", 260530) or 260530)
        blue_positions = [p for p in positions if int(getattr(p, "magic", 0) or 0) == blue_magic]
        lines.append(f"Existing Blue positions on {selected}: {len(blue_positions)}")
        if signal and sig_action in ["BUY", "SELL"]:
            for p in blue_positions:
                ptype = getattr(p, "type", None)
                if sig_action == "BUY" and ptype == getattr(mt5, "POSITION_TYPE_BUY", None):
                    blockers.append(f"Existing Blue BUY position already open on {selected}")
                if sig_action == "SELL" and ptype == getattr(mt5, "POSITION_TYPE_SELL", None):
                    blockers.append(f"Existing Blue SELL position already open on {selected}")
    except Exception as exc:
        warnings.append("Could not check existing positions: " + str(exc))

    # Dry-run broker validation.
    if run_order_check and not blockers:
        lines.append("\nBROKER DRY-RUN ORDER_CHECK")
        request, notes = _make_dry_request(selected, signal, action_override=action_override)
        for n in notes:
            warnings.append(n)
        if request is None:
            warnings.append("Could not build dry-run request")
        else:
            lines.append(f"Dry action    : {'BUY' if request.get('type') == getattr(mt5, 'ORDER_TYPE_BUY', -1) else 'SELL'}")
            lines.append(f"Dry volume    : {request.get('volume')} lots")
            lines.append(f"Dry price     : {request.get('price')}")
            lines.append(f"Dry SL/TP     : {request.get('sl')} / {request.get('tp')}")
            check = mt5.order_check(request)
            lines.append(f"order_check   : {check}")
            retcode = getattr(check, "retcode", None)
            ok_codes = [getattr(mt5, "TRADE_RETCODE_DONE", None), 0]
            if retcode not in ok_codes and retcode is not None:
                blockers.append(f"Broker order_check rejected dry request. Retcode={retcode}")

    return _finish(lines, blockers, warnings)


def _finish(lines: List[str], blockers: List[str], warnings: List[str]) -> str:
    lines.append("\nFINAL RESULT")
    if blockers:
        lines.append("ORDER WOULD NOT EXECUTE")
        lines.append("Blockers:")
        for b in blockers:
            lines.append(f"  - {b}")
    else:
        lines.append("ORDER MECHANICS LOOK OK")
        lines.append("No blocking issue found by doctor. If autopilot still skips, check its signal grade/confidence/news filters.")
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  ! {w}")
    lines.append("=" * 72)
    return "\n".join(lines)
