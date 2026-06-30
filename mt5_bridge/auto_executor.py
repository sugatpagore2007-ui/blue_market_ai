"""
Automatic MT5 execution guard for Blue Market AI.

Safety rules:
- terminal-only: never opens MT5
- demo-only by default
- confidence threshold
- max trades per day
- max daily loss percent
- spread check
- lot calculated from real MT5 broker specs
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:
    mt5 = None

from config import (
    AUTO_ORDER_EXECUTION,
    MIN_AUTO_TRADE_CONFIDENCE,
    AUTO_TRADE_DEMO_ONLY,
    AUTO_TRADE_ALLOW_REAL_ACCOUNT,
    AUTO_TRADE_RISK_PERCENT,
    MAX_AUTO_TRADES_PER_DAY,
    MAX_DAILY_LOSS_PERCENT,
    MAX_SPREAD_POINTS,
    AUTO_TRADE_USE_TP,
    MT5_STAGE2_EXECUTION_ENABLED,
    MT5_DEFAULT_DEVIATION,
    MT5_MAGIC_NUMBER,
    MT5_COMMENT,
)
from .terminal import ensure_connected, map_symbol, select_symbol, lot_size_from_broker
from .auto_manager import save_auto_trade_plan
from risk.session_trade_quota import can_place_trade, record_trade, quota_status_text
try:
    from diagnostics.self_healing_doctor import diagnose_order_message, log_event
except Exception:
    def diagnose_order_message(message):
        return ''
    def log_event(kind, message, details=None):
        return None

try:
    from config import MAX_SPREAD_POINTS_BY_SYMBOL
except Exception:
    MAX_SPREAD_POINTS_BY_SYMBOL = {}
try:
    from config import AUTO_TRADE_COUNT_ENTRY_DEALS_ONLY, ORDER_SEND_RETRY_ON_PRICE_CHANGE, ORDER_SEND_EXTRA_DEVIATION, ORDER_SEND_ONLY_IF_ORDER_CHECK_OK, ORDER_PUNCH_SHIELD_REFRESH_TICK_BEFORE_SEND
except Exception:
    AUTO_TRADE_COUNT_ENTRY_DEALS_ONLY = True
    ORDER_SEND_RETRY_ON_PRICE_CHANGE = True
    ORDER_SEND_EXTRA_DEVIATION = 50
    ORDER_SEND_ONLY_IF_ORDER_CHECK_OK = True
    ORDER_PUNCH_SHIELD_REFRESH_TICK_BEFORE_SEND = True


try:
    from config import AUTO_TRADE_DEMO_SERVER_KEYWORDS, AUTOPILOT_SEND_WITHOUT_SLTP_IF_BROKER_REJECTS_STOPS, AUTOPILOT_ATTACH_SLTP_AFTER_ENTRY
except Exception:
    AUTO_TRADE_DEMO_SERVER_KEYWORDS = ["demo", "trial", "practice"]
    AUTOPILOT_SEND_WITHOUT_SLTP_IF_BROKER_REJECTS_STOPS = True
    AUTOPILOT_ATTACH_SLTP_AFTER_ENTRY = True



def _account_is_demo() -> bool:
    """Best-effort demo detection.

    Some brokers report demo/trial servers differently through MT5. Blue stays
    demo-only, but recognizes server names such as Exness-MT5Trial11 as demo
    when the MT5 trade_mode enum is unavailable or unreliable.
    """
    if mt5 is None:
        return False
    acc = mt5.account_info()
    if acc is None:
        return False
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_const is not None and getattr(acc, "trade_mode", None) == demo_const:
        return True
    server = str(getattr(acc, "server", "") or "").lower()
    name = str(getattr(acc, "name", "") or "").lower()
    company = str(getattr(acc, "company", "") or "").lower()
    blob = " ".join([server, name, company])
    return any(str(k).lower() in blob for k in AUTO_TRADE_DEMO_SERVER_KEYWORDS)


def _today_deals_count_and_profit() -> Dict[str, Any]:
    """Return today's Blue entry-deal count and total Blue deal profit.

    Old builds counted *all* Blue deals. Partial closes, SL/TP exits and manager actions
    could quickly hit MAX_AUTO_TRADES_PER_DAY even when no new entries should be blocked.
    This version counts only entry deals for the trade-limit guard, while still using all
    Blue deal profit for daily-loss protection.
    """
    if mt5 is None:
        return {"count": 0, "profit": 0.0, "all_blue_deals": 0}
    end = datetime.now()
    start = datetime(end.year, end.month, end.day)
    deals = mt5.history_deals_get(start, end)
    if not deals:
        return {"count": 0, "profit": 0.0, "all_blue_deals": 0}

    blue_deals = []
    entry_deals = []
    entry_in_const = getattr(mt5, "DEAL_ENTRY_IN", None)
    for d in deals:
        comment = str(getattr(d, "comment", "") or "")
        magic = int(getattr(d, "magic", 0) or 0)
        is_blue = comment.startswith(MT5_COMMENT) or magic == int(MT5_MAGIC_NUMBER)
        if not is_blue:
            continue
        blue_deals.append(d)
        if AUTO_TRADE_COUNT_ENTRY_DEALS_ONLY and entry_in_const is not None:
            if getattr(d, "entry", None) == entry_in_const:
                entry_deals.append(d)
        else:
            # fallback: count positive volume market deals as entries only when no constant exists
            deal_type = getattr(d, "type", None)
            if deal_type in [getattr(mt5, "DEAL_TYPE_BUY", None), getattr(mt5, "DEAL_TYPE_SELL", None)]:
                entry_deals.append(d)

    profit = sum(float(getattr(d, "profit", 0.0) or 0.0) for d in blue_deals)
    return {"count": len(entry_deals), "profit": profit, "all_blue_deals": len(blue_deals)}

def auto_status_text() -> str:
    return (
        "Auto Execution Status\n"
        f"AUTO_ORDER_EXECUTION       : {AUTO_ORDER_EXECUTION}\n"
        f"MT5_STAGE2_EXECUTION_ENABLED: {MT5_STAGE2_EXECUTION_ENABLED}\n"
        f"MIN_AUTO_TRADE_CONFIDENCE  : {MIN_AUTO_TRADE_CONFIDENCE}%\n"
        f"AUTO_TRADE_DEMO_ONLY       : {AUTO_TRADE_DEMO_ONLY}\n"
        f"AUTO_TRADE_RISK_PERCENT    : {AUTO_TRADE_RISK_PERCENT}%\n"
        f"MAX_AUTO_TRADES_PER_DAY    : {MAX_AUTO_TRADES_PER_DAY}\n"
        f"MAX_DAILY_LOSS_PERCENT     : {MAX_DAILY_LOSS_PERCENT}%\n"
        f"MAX_SPREAD_POINTS          : {MAX_SPREAD_POINTS}\n"
        f"SESSION_QUOTA              : 2/day total; 1 Gold slot (A+ or 100%); 1 other-pair slot"
    )



def _max_spread_for_symbol(symbol: str) -> float:
    """Return asset-specific max spread. Fixes XAUUSDm being blocked by forex limit."""
    name = (symbol or "").upper()
    # direct first
    if name in MAX_SPREAD_POINTS_BY_SYMBOL:
        return float(MAX_SPREAD_POINTS_BY_SYMBOL[name])
    # base without common Exness suffix m
    base = name[:-1] if name.endswith("M") else name
    if base in MAX_SPREAD_POINTS_BY_SYMBOL:
        return float(MAX_SPREAD_POINTS_BY_SYMBOL[base])
    for key, val in MAX_SPREAD_POINTS_BY_SYMBOL.items():
        k = str(key).upper()
        if name.startswith(k) or k.startswith(base):
            return float(val)
    return float(MAX_SPREAD_POINTS)


def _normalize_price(symbol: str, price: float) -> float:
    info = mt5.symbol_info(symbol) if mt5 else None
    digits = int(getattr(info, "digits", 5) or 5) if info else 5
    return round(float(price), digits)


def _order_prices_are_valid(action: str, price: float, sl: float, tp: float) -> tuple[bool, str]:
    action = action.upper()
    if action == "BUY" and not (sl < price < tp):
        return False, f"Invalid BUY prices. Need SL < market price < TP, got SL={sl}, price={price}, TP={tp}."
    if action == "SELL" and not (tp < price < sl):
        return False, f"Invalid SELL prices. Need TP < market price < SL, got TP={tp}, price={price}, SL={sl}."
    return True, "prices valid"



def _existing_same_direction_position(symbol: str, action: str) -> bool:
    """Avoid duplicate Blue positions in the same direction for the same MT5 symbol."""
    if mt5 is None:
        return False
    positions = mt5.positions_get(symbol=symbol) or []
    for pos in positions:
        if int(getattr(pos, "magic", 0) or 0) != int(MT5_MAGIC_NUMBER):
            continue
        ptype = getattr(pos, "type", None)
        if action == "BUY" and ptype == mt5.POSITION_TYPE_BUY:
            return True
        if action == "SELL" and ptype == mt5.POSITION_TYPE_SELL:
            return True
    return False


def _minimum_stop_distance(symbol: str) -> float:
    info = mt5.symbol_info(symbol) if mt5 else None
    if info is None:
        return 0.0
    point = float(getattr(info, "point", 0.0) or 0.0)
    stops = float(getattr(info, "trade_stops_level", 0.0) or 0.0)
    freeze = float(getattr(info, "trade_freeze_level", 0.0) or 0.0)
    return max(stops, freeze, 1.0) * point


def _rebuild_levels_around_market(symbol: str, action: str, market_price: float, signal: Dict[str, Any]) -> tuple[float, float, str]:
    """Rebuild SL/TP around live broker price.

    This fixes XAUUSDm orders when analysis data comes from Yahoo GC futures but execution is on
    Exness spot-style XAUUSDm. Absolute Yahoo levels can be slightly misaligned with MT5 price.
    We preserve the signal's risk distance and R target, but anchor everything to live bid/ask.
    """
    sig_entry = _safe_float(signal.get("entry"), market_price)
    sig_sl = _safe_float(signal.get("stop_loss"), market_price)
    tp_key = AUTO_TRADE_USE_TP if AUTO_TRADE_USE_TP in ["target_1", "target_2"] else "target_1"
    sig_tp = _safe_float(signal.get(tp_key) or signal.get("target_1"), market_price)
    raw_risk = abs(sig_entry - sig_sl)
    min_dist = _minimum_stop_distance(symbol)
    if raw_risk <= 0:
        raw_risk = max(abs(market_price) * 0.002, min_dist * 3)
    raw_risk = max(raw_risk, min_dist * 3 if min_dist else raw_risk)
    rr = abs(sig_tp - sig_entry) / abs(sig_entry - sig_sl) if abs(sig_entry - sig_sl) > 0 else 2.0
    rr = max(1.0, min(5.0, rr))
    if action == "BUY":
        sl = market_price - raw_risk
        tp = market_price + raw_risk * rr
    else:
        sl = market_price + raw_risk
        tp = market_price - raw_risk * rr
    return _normalize_price(symbol, sl), _normalize_price(symbol, tp), f"rebased around live MT5 price; risk distance {round(raw_risk, 5)}, RR {round(rr, 2)}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _result_ok(result: Any) -> bool:
    retcode = getattr(result, "retcode", None)
    return retcode in [getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)]


def _order_check_ok(check: Any) -> bool:
    """MT5 order_check success varies by broker. Accept DONE/PLACED/0 when provided."""
    retcode = getattr(check, "retcode", None)
    ok_codes = {
        getattr(mt5, "TRADE_RETCODE_DONE", None),
        getattr(mt5, "TRADE_RETCODE_PLACED", None),
        0,
    }
    return retcode in ok_codes


def _refresh_request_tick(req: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh bid/ask just before order_check/order_send to reduce requote/off-price failures."""
    if not ORDER_PUNCH_SHIELD_REFRESH_TICK_BEFORE_SEND:
        return req
    try:
        tick = mt5.symbol_info_tick(req["symbol"])
        if tick is not None:
            req = dict(req)
            req["price"] = float(tick.ask if req["type"] == mt5.ORDER_TYPE_BUY else tick.bid)
    except Exception:
        pass
    return req


def _send_with_filling_fallback(request: Dict[str, Any]) -> tuple[Any, list[str]]:
    """Try order_send with several filling modes and keep clear diagnostics.

    Earlier Blue printed "AUTO TRADE SENT" even when MT5 rejected the request. This returns
    the actual MT5 result plus readable check/send details so terminal output tells the truth.
    """
    modes = []
    for name in ["ORDER_FILLING_IOC", "ORDER_FILLING_FOK", "ORDER_FILLING_RETURN"]:
        v = getattr(mt5, name, None)
        if v is not None and v not in modes:
            modes.append(v)

    diagnostics: list[str] = []
    last_result = None
    for mode in modes:
        req = dict(request)
        req["type_filling"] = mode
        req = _refresh_request_tick(req)
        mode_name = str(mode)
        check = mt5.order_check(req)
        diagnostics.append(f"order_check filling={mode_name}: {check}")
        if ORDER_SEND_ONLY_IF_ORDER_CHECK_OK and not _order_check_ok(check):
            diagnostics.append(f"order_send skipped filling={mode_name}: Order Punch Shield blocked because order_check did not pass.")
            last_result = check
            continue
        result = mt5.order_send(req)
        last_result = result
        diagnostics.append(f"order_send  filling={mode_name}: {result}")
        if _result_ok(result):
            return result, diagnostics

        # If broker says requote/price changed/off quotes, refresh price once and retry.
        retcode = getattr(result, "retcode", None)
        price_error_codes = {
            getattr(mt5, "TRADE_RETCODE_REQUOTE", None),
            getattr(mt5, "TRADE_RETCODE_PRICE_CHANGED", None),
            getattr(mt5, "TRADE_RETCODE_PRICE_OFF", None),
        }
        if ORDER_SEND_RETRY_ON_PRICE_CHANGE and retcode in price_error_codes:
            tick = mt5.symbol_info_tick(req["symbol"])
            if tick is not None:
                req["price"] = float(tick.ask if req["type"] == mt5.ORDER_TYPE_BUY else tick.bid)
                req["deviation"] = int(req.get("deviation", MT5_DEFAULT_DEVIATION)) + int(ORDER_SEND_EXTRA_DEVIATION)
                retry = mt5.order_send(req)
                last_result = retry
                diagnostics.append(f"retry_send refreshed_price filling={mode_name}: {retry}")
                if _result_ok(retry):
                    return retry, diagnostics
    return last_result, diagnostics

def _guard_checks(signal: Dict[str, Any]) -> Dict[str, Any]:
    if not AUTO_ORDER_EXECUTION:
        return {"ok": False, "message": "Auto execution is OFF in config.py."}
    if not MT5_STAGE2_EXECUTION_ENABLED:
        return {"ok": False, "message": "Stage 2 MT5 execution is OFF. Set MT5_STAGE2_EXECUTION_ENABLED=True after testing."}
    action = str(signal.get("action", "WAIT")).upper()
    if action not in ["BUY", "SELL"]:
        return {"ok": False, "message": "No auto order because signal is WAIT/no-trade."}
    confidence = float(signal.get("confidence", 0))
    if confidence < float(MIN_AUTO_TRADE_CONFIDENCE):
        return {"ok": False, "message": f"No auto order. Confidence {confidence}% is below {MIN_AUTO_TRADE_CONFIDENCE}%."}

    ok, msg = ensure_connected()
    if not ok:
        return {"ok": False, "message": msg}

    acc = mt5.account_info()
    if acc is None:
        return {"ok": False, "message": "No MT5 account info available."}
    if AUTO_TRADE_DEMO_ONLY and not _account_is_demo() and not AUTO_TRADE_ALLOW_REAL_ACCOUNT:
        return {"ok": False, "message": "Auto execution blocked: MT5 account is not demo. Keep demo-only protection on for testing."}

    day = _today_deals_count_and_profit()
    if day["count"] >= int(MAX_AUTO_TRADES_PER_DAY):
        return {"ok": False, "message": f"Daily auto trade limit reached: {day['count']} trades."}
    quota = can_place_trade(symbol=signal.get("symbol") or signal.get("ticker"), signal=signal)
    if not quota.get("ok"):
        return {"ok": False, "message": "Session/category quota blocked: " + quota.get("message", "quota failed")}
    daily_loss_limit = -abs(float(acc.balance) * float(MAX_DAILY_LOSS_PERCENT) / 100.0)
    if day["profit"] <= daily_loss_limit:
        return {"ok": False, "message": f"Daily loss guard active. Today P/L {round(day['profit'], 2)} <= {round(daily_loss_limit, 2)}."}

    ok_sel, sym = select_symbol(signal.get("ticker") or signal.get("symbol"))
    if not ok_sel:
        return {"ok": False, "message": f"Could not select MT5 symbol {sym}. Check Exness suffix, example XAUUSDm/EURUSDm/BTCUSDm."}
    info = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    if info is None or tick is None:
        return {"ok": False, "message": f"Missing symbol/tick data for {sym}."}
    spread_now = float(getattr(info, "spread", 0) or 0)
    spread_limit = _max_spread_for_symbol(sym)
    if spread_now > spread_limit:
        return {"ok": False, "message": f"Spread too high for {sym}: {spread_now} points > {spread_limit}."}
    return {"ok": True, "message": "All auto execution guard checks passed.", "account": acc, "symbol": sym, "tick": tick}



def _format_mt5_result(result: Any) -> str:
    if result is None:
        return "None"
    try:
        return str(result)
    except Exception:
        return repr(result)


def _send_market_without_sltp_then_attach(request: Dict[str, Any], sl: float, tp: float) -> tuple[Any, list[str]]:
    """Fallback for brokers that reject SL/TP in the first market order.

    Some MT5 brokers reject initial requests with SL/TP because of stop/freeze
    distance or filling rules, even when a plain market order is accepted. This
    sends the demo market order without SL/TP, then attempts an SLTP modification.
    """
    diagnostics: list[str] = []
    plain = dict(request)
    plain["sl"] = 0.0
    plain["tp"] = 0.0
    result, diags = _send_with_filling_fallback(plain)
    diagnostics.extend(["NO-SLTP FALLBACK:" ] + diags)
    if not _result_ok(result):
        return result, diagnostics
    if not AUTOPILOT_ATTACH_SLTP_AFTER_ENTRY:
        return result, diagnostics
    # Find the newest Blue position on this symbol and attach SL/TP.
    try:
        positions = mt5.positions_get(symbol=plain["symbol"]) or []
        blue_positions = [p for p in positions if int(getattr(p, "magic", 0) or 0) == int(MT5_MAGIC_NUMBER)]
        if not blue_positions:
            diagnostics.append("SLTP attach skipped: order filled but Blue position not found yet.")
            return result, diagnostics
        pos = sorted(blue_positions, key=lambda x: int(getattr(x, "time", 0) or 0), reverse=True)[0]
        modify_req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(getattr(pos, "ticket")),
            "symbol": plain["symbol"],
            "sl": float(sl),
            "tp": float(tp),
            "magic": MT5_MAGIC_NUMBER,
            "comment": MT5_COMMENT + " AUTO SLTP",
        }
        mod = mt5.order_send(modify_req)
        diagnostics.append(f"attach SLTP result: {_format_mt5_result(mod)}")
    except Exception as exc:
        diagnostics.append(f"attach SLTP error: {exc}")
    return result, diagnostics

def execute_signal_if_allowed(signal: Dict[str, Any]) -> str:
    """Place an MT5 market order automatically only when all safeguards pass."""
    guards = _guard_checks(signal)
    if not guards.get("ok"):
        msg = "AUTO TRADE SKIPPED: " + guards.get("message", "guard failed")
        log_event("order_guard", msg, {"signal": {"symbol": signal.get("symbol"), "action": signal.get("action"), "confidence": signal.get("confidence")}})
        note = diagnose_order_message(msg)
        return msg + ("\n" + note if note else "")

    acc = guards["account"]
    sym = guards["symbol"]
    tick = guards["tick"]
    action = str(signal.get("action")).upper()
    # Use live MT5 bid/ask as real market entry for execution and broker lot sizing.
    # For XAUUSDm, Yahoo GC=F levels may not match Exness spot exactly, so SL/TP are
    # rebased around live MT5 price while preserving the signal risk distance and RR.
    action = str(signal.get("action")).upper()
    if _existing_same_direction_position(sym, action):
        msg = f"AUTO TRADE SKIPPED: existing Blue {action} position already open on {sym}."
        log_event("order_guard", msg, {"symbol": sym, "action": action})
        return msg + "\n" + diagnose_order_message(msg)
    market_price = float(tick.ask if action == "BUY" else tick.bid)
    entry = _normalize_price(sym, market_price)
    sl, tp, level_note = _rebuild_levels_around_market(sym, action, entry, signal)
    ok_prices, price_msg = _order_prices_are_valid(action, entry, sl, tp)
    if not ok_prices:
        msg = "AUTO TRADE SKIPPED: " + price_msg
        log_event("order_guard", msg, {"symbol": sym, "action": action})
        return msg + "\n" + diagnose_order_message(msg)

    lot = lot_size_from_broker(sym, float(acc.balance), float(AUTO_TRADE_RISK_PERCENT), entry, sl)
    if not lot.get("ok") or not lot.get("tradable"):
        msg = "AUTO TRADE SKIPPED: " + lot.get("message", "lot not tradable")
        log_event("order_guard", msg, {"symbol": sym, "action": action})
        return msg + "\n" + diagnose_order_message(msg)
    volume = float(lot.get("recommended_lot_size", 0))
    if volume <= 0:
        msg = "AUTO TRADE SKIPPED: broker lot size is zero."
        log_event("order_guard", msg, {"symbol": sym, "action": action})
        return msg + "\n" + diagnose_order_message(msg)

    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    price = entry
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": sym,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": MT5_DEFAULT_DEVIATION,
        "magic": MT5_MAGIC_NUMBER,
        "comment": MT5_COMMENT + " AUTO",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result, diagnostics = _send_with_filling_fallback(request)
    if (not _result_ok(result)) and AUTOPILOT_SEND_WITHOUT_SLTP_IF_BROKER_REJECTS_STOPS:
        fallback_result, fallback_diags = _send_market_without_sltp_then_attach(request, sl, tp)
        diagnostics.extend(fallback_diags)
        if _result_ok(fallback_result):
            result = fallback_result
    retcode = getattr(result, "retcode", None)
    try:
        # Save local TP1/TP2 plan so auto manager can partial close and trail later.
        success_codes = [getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)]
        if retcode in success_codes:
            save_auto_trade_plan(signal, result, sym)
            try:
                record_trade(sym, action, ticket=getattr(result, "order", None) or getattr(result, "deal", None), signal=signal)
            except Exception:
                pass
    except Exception:
        pass
    success = _result_ok(result)
    title = "AUTO TRADE DONE" if success else "AUTO TRADE FAILED"
    last_error = mt5.last_error() if mt5 else None
    diag_text = "\n".join(diagnostics[-6:]) if diagnostics else "No diagnostics."
    healing_note = "" if success else "\n" + diagnose_order_message(str(result) + " " + str(last_error) + " " + diag_text)
    log_event("order_result", title, {"symbol": sym, "action": action, "success": success, "retcode": retcode, "last_error": str(last_error)})
    return (
        f"{title}\n"
        f"Symbol    : {sym}\n"
        f"Action    : {action}\n"
        f"Confidence: {signal.get('confidence')}%\n"
        f"Lot       : {volume}\n"
        f"Price     : {price}\n"
        f"SL / TP   : {sl} / {tp}\n"
        f"Level note: {level_note}\n"
        f"Risk %    : {AUTO_TRADE_RISK_PERCENT}%\n"
        f"Retcode   : {retcode}\n"
        f"Last error: {last_error}\n"
        f"MT5 result: {result}\n"
        f"Diagnostics:\n{diag_text}\n"
        f"Next check : type order doctor {sym} if order is still not punching."
        f"{healing_note}"
    )
