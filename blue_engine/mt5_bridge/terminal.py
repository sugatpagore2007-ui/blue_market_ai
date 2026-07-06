"""
MT5 terminal-only bridge for Blue Market AI.

Important design choice:
- This module never starts or pops up the MT5 terminal.
- User must keep MT5 already open and logged in.
- If MetaTrader5 is missing or terminal is not connected, functions fail safely.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math
import os
import subprocess
import ctypes

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # package may not be installed on non-Windows systems
    mt5 = None

from config import MT5_SYMBOL_MAP, MT5_DEFAULT_DEVIATION, MT5_MAGIC_NUMBER, MT5_COMMENT, MT5_STAGE2_EXECUTION_ENABLED
try:
    from config import MT5_SUPPRESS_WINDOW_POPUPS, MT5_MINIMIZE_AFTER_CONNECT, MT5_REUSE_EXISTING_CONNECTION
except Exception:
    MT5_SUPPRESS_WINDOW_POPUPS = True
    MT5_MINIMIZE_AFTER_CONNECT = True
    MT5_REUSE_EXISTING_CONNECTION = True
try:
    from config import MT5_SYMBOL_ALIASES, MT5_SYMBOL_SUFFIX
except Exception:
    MT5_SYMBOL_ALIASES = {}
    MT5_SYMBOL_SUFFIX = ""

from .broker_profiles import active_profile, broker_status_text, set_broker_profile_text


@dataclass
class MT5Status:
    ok: bool
    message: str


_MT5_CONNECTED_CACHE = False


def _account_ready() -> bool:
    """Return True if the Python MT5 bridge already has a live account session."""
    if mt5 is None:
        return False
    try:
        acc = mt5.account_info()
        term = mt5.terminal_info()
        return acc is not None and term is not None and bool(getattr(term, "connected", True))
    except Exception:
        return False


def _suppress_mt5_window() -> None:
    """Best-effort: keep MT5/Exness minimized/no-focus after API connection.

    The MetaTrader5 package may bring the terminal forward when initialize() is called.
    Blue is terminal-only, so this quietly minimizes known MT5/Exness windows after connect.
    It does not launch MT5 and it does not close anything.
    """
    if os.name != "nt" or not MT5_SUPPRESS_WINDOW_POPUPS:
        return
    try:
        user32 = ctypes.windll.user32
        SW_MINIMIZE = 6
        titles = []

        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        GetWindowTextW = user32.GetWindowTextW
        IsWindowVisible = user32.IsWindowVisible
        ShowWindow = user32.ShowWindow

        def callback(hwnd, lParam):
            if not IsWindowVisible(hwnd):
                return True
            length = GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            if any(k in title for k in ["metatrader", "meta trader", "exness", "mt5"]):
                titles.append(buff.value)
                if MT5_MINIMIZE_AFTER_CONNECT:
                    ShowWindow(hwnd, SW_MINIMIZE)
            return True

        EnumWindows(EnumWindowsProc(callback), 0)
    except Exception:
        pass


def is_available() -> bool:
    return mt5 is not None


def _mt5_terminal_process_running() -> bool:
    """Best-effort check that an MT5/Exness terminal is already open.

    Different brokers name the process differently, so this check is intentionally
    broader than only terminal64.exe. It is used for diagnostics only; the real
    connection test is mt5.initialize() + account_info().
    """
    if os.name != "nt":
        return True
    try:
        out = subprocess.check_output(["tasklist", "/fo", "csv", "/nh"], text=True, errors="ignore")
        low = out.lower()
        known = ["terminal64.exe", "terminal.exe", "metatrader", "meta trader", "exness"]
        return any(k in low for k in known)
    except Exception:
        return False


def connect() -> MT5Status:
    """Attach to the already logged-in MT5 terminal without popping the MT5 window.

    Important: Blue never launches MT5. It also reuses an existing initialized
    connection so autopilot cycles do not keep calling mt5.initialize(), because
    repeated initialize calls can bring the MT5/Exness window to the front.
    """
    global _MT5_CONNECTED_CACHE
    if mt5 is None:
        return MT5Status(False, "MetaTrader5 Python package is not installed. Run: pip install MetaTrader5")

    if MT5_REUSE_EXISTING_CONNECTION and (_MT5_CONNECTED_CACHE or _account_ready()):
        acc = mt5.account_info()
        if acc is not None:
            return MT5Status(True, f"MT5 already connected terminal-only. Account {acc.login}, server {acc.server}, balance {round(acc.balance, 2)}")

    process_seen = _mt5_terminal_process_running()
    ok = mt5.initialize()
    if not ok:
        err = mt5.last_error()
        return MT5Status(False, f"MT5 not connected. Open MT5 manually, log in, then run connect mt5. Error: {err}")

    info = mt5.terminal_info()
    acc = mt5.account_info()
    if info is None or acc is None:
        return MT5Status(False, "MT5 initialized but account/terminal info is unavailable. Check login and broker connection.")

    _MT5_CONNECTED_CACHE = True
    _suppress_mt5_window()
    note = "process detected" if process_seen else "process name not detected, but MT5 API attached successfully"
    return MT5Status(True, f"Connected to MT5 terminal-only. Account {acc.login}, server {acc.server}, balance {round(acc.balance, 2)} ({note})")


def diagnose_text() -> str:
    if mt5 is None:
        return "MT5 Diagnose\nMetaTrader5 package: NOT INSTALLED\nRun: pip install MetaTrader5"
    process_seen = _mt5_terminal_process_running()
    ok = _account_ready()
    if not ok:
        ok = mt5.initialize()
        if ok:
            _suppress_mt5_window()
    err = mt5.last_error() if not ok else None
    acc = mt5.account_info() if ok else None
    term = mt5.terminal_info() if ok else None
    profile = active_profile()
    lines = ["MT5 Diagnose", f"Broker profile      : {profile.get('name')} — {profile.get('label')}", f"MetaTrader5 package : INSTALLED", f"Process detected    : {'YES' if process_seen else 'NO / UNKNOWN'}", f"Initialize          : {'TRUE' if ok else 'FALSE'}"]
    if err:
        lines.append(f"Last error          : {err}")
    if acc:
        lines += [
            f"Login               : {acc.login}",
            f"Server              : {acc.server}",
            f"Balance             : {round(acc.balance, 2)} {acc.currency}",
            f"Trade allowed       : {getattr(acc, 'trade_allowed', 'unknown')}",
            f"Expert allowed      : {getattr(acc, 'trade_expert', 'unknown')}",
        ]
    if term:
        lines += [
            f"Terminal connected  : {getattr(term, 'connected', 'unknown')}",
            f"Trade allowed term  : {getattr(term, 'trade_allowed', 'unknown')}",
            f"Terminal path       : {getattr(term, 'path', '')}",
        ]
    return "\n".join(lines)


def symbols_text(filter_text: str = "") -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    syms = mt5.symbols_get() or []
    filt = (filter_text or "").upper().strip()
    names = [s.name for s in syms if not filt or filt in s.name.upper()]
    if not names:
        return f"No MT5 symbols found for filter: {filter_text}"
    shown = names[:120]
    suffix = "" if len(names) <= 120 else f"\n...and {len(names)-120} more. Use: show mt5 symbols xau / eur / btc"
    return "MT5 Symbols" + (f" matching {filter_text}" if filter_text else "") + "\n" + ", ".join(shown) + suffix


def shutdown() -> str:
    global _MT5_CONNECTED_CACHE
    if mt5 is None:
        return "MetaTrader5 package not installed."
    mt5.shutdown()
    _MT5_CONNECTED_CACHE = False
    return "MT5 bridge disconnected."


def ensure_connected() -> Tuple[bool, str]:
    status = connect()
    return status.ok, status.message


def account_summary() -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    acc = mt5.account_info()
    if acc is None:
        return "No MT5 account info available."
    return (
        "MT5 Account\n"
        f"Login      : {acc.login}\n"
        f"Server     : {acc.server}\n"
        f"Currency   : {acc.currency}\n"
        f"Balance    : {round(acc.balance, 2)}\n"
        f"Equity     : {round(acc.equity, 2)}\n"
        f"Margin     : {round(acc.margin, 2)}\n"
        f"Free margin: {round(acc.margin_free, 2)}\n"
        f"Leverage   : 1:{acc.leverage}"
    )


def _clean_symbol_text(value: str) -> str:
    return (value or '').strip().upper().replace('/', '').replace(' ', '').replace('-', '')


def _profile_maps() -> tuple[dict, dict, str, str]:
    """Return active broker symbol map/aliases/suffix/platform.

    This makes Blue broker-independent for MT5 brokers. Use:
    broker set auto / exness / xm / icmarkets / generic_mt5
    """
    profile = active_profile()
    symbol_map = dict(MT5_SYMBOL_MAP)
    # active profile overrides config map, unless profile map is empty (auto mode)
    if profile.get("symbol_map"):
        symbol_map.update(profile.get("symbol_map") or {})
    aliases = dict(MT5_SYMBOL_ALIASES or {})
    aliases.update(profile.get("aliases") or {})
    suffix = profile.get("suffix", MT5_SYMBOL_SUFFIX or "")
    platform = profile.get("platform", "mt5")
    return symbol_map, aliases, suffix, platform


def map_symbol(ticker_or_name: str) -> str:
    """Map Yahoo/Blue symbols to the active broker symbol style.

    Works with Exness, XM, IC Markets and generic MT5 brokers by combining:
    - configured broker profile map
    - profile suffix
    - dynamic broker symbol discovery in resolve_mt5_symbol()
    """
    symbol_map, aliases, suffix, platform = _profile_maps()
    key = (ticker_or_name or '').strip()
    if key in symbol_map:
        return symbol_map[key]
    clean = _clean_symbol_text(key)
    yahoo_to_base = {
        'GCF': 'XAUUSD', 'SIF': 'XAGUSD', 'EURUSDX': 'EURUSD', 'GBPUSDX': 'GBPUSD',
        'JPYX': 'USDJPY', 'BTCUSD': 'BTCUSD', 'ETHUSD': 'ETHUSD', 'CLF': 'USOIL',
        'NQF': 'NAS100', 'ESF': 'US500', 'DXYNYB': 'DXY',
    }
    base = yahoo_to_base.get(clean, clean)
    if suffix and base and not base.endswith(str(suffix).upper()):
        return base + str(suffix)
    return base


def resolve_mt5_symbol(ticker_or_name: str) -> Optional[str]:
    """Find the real MT5 symbol name in this broker account.

    Tries configured map, aliases, suffix forms, then scans Market Watch/all symbols.
    """
    if mt5 is None:
        return None
    preferred = map_symbol(ticker_or_name)
    candidates = []
    def add(x):
        if x and x not in candidates:
            candidates.append(x)
    add(preferred)
    clean_pref = _clean_symbol_text(preferred)
    symbol_map, aliases, suffix, platform = _profile_maps()
    base = clean_pref[:-len(suffix)] if suffix and clean_pref.endswith(str(suffix).upper()) else clean_pref
    for x in aliases.get(base, []):
        add(x)
    if suffix:
        add(base + str(suffix))
    add(base)
    # Direct candidates first
    for sym in candidates:
        info = mt5.symbol_info(sym)
        if info is not None:
            return sym
    # Scan all broker symbols and match by normalized base, allowing suffixes like m, .m, _m
    try:
        all_symbols = mt5.symbols_get() or []
        wanted = base.upper()
        for s in all_symbols:
            name = getattr(s, 'name', '')
            norm = _clean_symbol_text(name).replace('.', '')
            if norm == wanted or norm.startswith(wanted):
                return name
    except Exception:
        pass
    return preferred


def select_symbol(ticker_or_name: str) -> Tuple[bool, str]:
    sym = resolve_mt5_symbol(ticker_or_name) or map_symbol(ticker_or_name)
    if mt5 is None:
        return False, sym
    ok = bool(mt5.symbol_select(sym, True))
    return ok, sym


def symbol_info_text(symbol: str) -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    ok_sel, sym = select_symbol(symbol)
    info = mt5.symbol_info(sym)
    if info is None or not ok_sel:
        return f"MT5 symbol {sym} not found/selected. Check broker symbol name, example: XAUUSDm, EURUSDm, BTCUSDm."
    tick = mt5.symbol_info_tick(sym)
    bid = getattr(tick, 'bid', None) if tick else None
    ask = getattr(tick, 'ask', None) if tick else None
    return (
        f"MT5 Symbol Spec: {sym}\n"
        f"Bid/Ask       : {bid} / {ask}\n"
        f"Digits        : {info.digits}\n"
        f"Point         : {info.point}\n"
        f"Contract size : {info.trade_contract_size}\n"
        f"Tick size     : {info.trade_tick_size}\n"
        f"Tick value    : {info.trade_tick_value}\n"
        f"Min volume    : {info.volume_min}\n"
        f"Volume step   : {info.volume_step}\n"
        f"Max volume    : {info.volume_max}\n"
        f"Spread        : {info.spread} points"
    )


def live_price(symbol: str) -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    ok_sel, sym = select_symbol(symbol)
    if not ok_sel:
        return f"Could not select {sym} in MT5 Market Watch. Check suffix, example XAUUSDm or EURUSDm."
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return f"No live tick for {sym}."
    return f"{sym} live price — Bid: {tick.bid}, Ask: {tick.ask}, Last: {getattr(tick, 'last', 0)}"


def positions_text() -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get()
    if positions is None:
        return "Could not read MT5 positions."
    if len(positions) == 0:
        return "No open MT5 positions."
    lines = ["Open MT5 Positions"]
    for p in positions:
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        lines.append(
            f"#{p.ticket} {p.symbol} {side} {p.volume} lots | entry {p.price_open} | SL {p.sl} | TP {p.tp} | profit {round(p.profit, 2)}"
        )
    return "\n".join(lines)


def history_text(days: int = 7) -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=days)
    deals = mt5.history_deals_get(start, end)
    if deals is None:
        return "Could not read MT5 trade history."
    if len(deals) == 0:
        return f"No MT5 trade history found in last {days} days."
    total_profit = sum(getattr(d, 'profit', 0.0) for d in deals)
    lines = [f"MT5 Trade History — last {days} days", f"Deals: {len(deals)} | Net profit: {round(total_profit, 2)}"]
    for d in list(deals)[-10:]:
        lines.append(f"{d.symbol} volume {d.volume} price {d.price} profit {round(d.profit, 2)} comment {d.comment}")
    return "\n".join(lines)


def _round_volume(volume: float, step: float, min_volume: float, max_volume: float) -> float:
    if step <= 0:
        step = 0.01
    rounded = math.floor(volume / step) * step
    rounded = max(0.0, min(rounded, max_volume))
    # determine decimals from step
    decimals = max(0, min(8, len(str(step).split('.')[-1]) if '.' in str(step) else 0))
    return round(rounded, decimals)


def lot_size_from_broker(symbol: str, balance: float, risk_percent: float, entry: float, stop_loss: float) -> Dict[str, Any]:
    ok, msg = ensure_connected()
    if not ok:
        return {"ok": False, "message": msg}
    ok_sel, sym = select_symbol(symbol)
    if not ok_sel:
        return {"ok": False, "message": f"Could not select {sym}. Check your Exness suffix, example XAUUSDm/EURUSDm."}
    info = mt5.symbol_info(sym)
    if info is None:
        return {"ok": False, "message": f"No MT5 symbol info for {sym}."}
    risk_cash = float(balance) * float(risk_percent) / 100.0
    price_distance = abs(float(entry) - float(stop_loss))
    tick_size = float(info.trade_tick_size or info.point or 0)
    tick_value = float(info.trade_tick_value or 0)
    if price_distance <= 0 or tick_size <= 0 or tick_value <= 0:
        return {"ok": False, "message": f"Cannot calculate broker lot for {sym}. Missing tick value/tick size."}
    risk_per_lot = (price_distance / tick_size) * tick_value
    raw_volume = risk_cash / risk_per_lot if risk_per_lot else 0.0
    volume = _round_volume(raw_volume, float(info.volume_step), float(info.volume_min), float(info.volume_max))
    tradable = volume >= float(info.volume_min)
    actual_risk = volume * risk_per_lot
    return {
        "ok": True,
        "symbol": sym,
        "balance": round(float(balance), 2),
        "risk_percent": round(float(risk_percent), 2),
        "risk_cash": round(risk_cash, 2),
        "entry": float(entry),
        "stop_loss": float(stop_loss),
        "price_distance": round(price_distance, int(info.digits or 5)),
        "tick_size": tick_size,
        "tick_value": tick_value,
        "risk_per_lot": round(risk_per_lot, 2),
        "raw_volume": round(raw_volume, 6),
        "recommended_lot_size": volume if tradable else 0.0,
        "min_volume": info.volume_min,
        "volume_step": info.volume_step,
        "max_volume": info.volume_max,
        "actual_risk": round(actual_risk, 2),
        "tradable": tradable,
        "message": (f"Use {volume} lots on {sym}. Estimated risk about {round(actual_risk, 2)}." if tradable else f"Calculated lot {round(raw_volume, 6)} is below broker minimum {info.volume_min}."),
    }


def format_broker_lot(result: Dict[str, Any]) -> str:
    if not result.get('ok'):
        return result.get('message', 'MT5 lot calculation failed.')
    return (
        f"MT5 Broker Lot Size for {result['symbol']}\n"
        f"Balance        : {result['balance']}\n"
        f"Risk %         : {result['risk_percent']}\n"
        f"Risk cash      : {result['risk_cash']}\n"
        f"Entry / SL     : {result['entry']} / {result['stop_loss']}\n"
        f"Risk per lot   : {result['risk_per_lot']}\n"
        f"Recommended lot: {result['recommended_lot_size']}\n"
        f"Actual risk    : {result['actual_risk']}\n"
        f"Note           : {result['message']}"
    )


def stage2_enabled() -> bool:
    return bool(MT5_STAGE2_EXECUTION_ENABLED)


def _order_type(action: str):
    action = action.upper().strip()
    if action == 'BUY':
        return mt5.ORDER_TYPE_BUY
    if action == 'SELL':
        return mt5.ORDER_TYPE_SELL
    raise ValueError('action must be BUY or SELL')


def place_market_order(symbol: str, action: str, volume: float, sl: float, tp: float, comment: str = MT5_COMMENT) -> str:
    """Stage 2. Protected order placement. No chart/terminal popup. Terminal must already be open."""
    if not stage2_enabled():
        return "Stage 2 execution is disabled. Set MT5_STAGE2_EXECUTION_ENABLED=True in config.py only after demo testing."
    ok, msg = ensure_connected()
    if not ok:
        return msg
    ok_sel, sym = select_symbol(symbol)
    if not ok_sel:
        return f"Could not select {sym}. Check your Exness suffix, example XAUUSDm/EURUSDm."
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return f"No live tick for {sym}."
    typ = _order_type(action)
    price = tick.ask if typ == mt5.ORDER_TYPE_BUY else tick.bid
    confirm = input(f"CONFIRM {action.upper()} {volume} lots {sym} at market, SL {sl}, TP {tp}? Type EXECUTE: ").strip()
    if confirm != 'EXECUTE':
        return "Order cancelled."
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": sym,
        "volume": float(volume),
        "type": typ,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": MT5_DEFAULT_DEVIATION,
        "magic": MT5_MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    return f"MT5 order result: {result}"


def modify_position(ticket: int, sl: Optional[float] = None, tp: Optional[float] = None, confirm: bool = True) -> str:
    if not stage2_enabled():
        return "Stage 2 execution is disabled."
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return f"Position {ticket} not found."
    p = positions[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": int(ticket),
        "symbol": p.symbol,
        "sl": float(sl if sl is not None else p.sl),
        "tp": float(tp if tp is not None else p.tp),
        "magic": MT5_MAGIC_NUMBER,
        "comment": MT5_COMMENT,
    }
    if confirm:
        user_confirm = input(f"CONFIRM modify #{ticket} SL {request['sl']} TP {request['tp']}? Type EXECUTE: ").strip()
        if user_confirm != 'EXECUTE':
            return "Modification cancelled."
    return f"MT5 modify result: {mt5.order_send(request)}"


def close_position(ticket: int, partial_volume: Optional[float] = None, confirm: bool = True) -> str:
    if not stage2_enabled():
        return "Stage 2 execution is disabled."
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return f"Position {ticket} not found."
    p = positions[0]
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return f"No tick for {p.symbol}."
    close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask
    volume = float(partial_volume or p.volume)
    if confirm:
        user_confirm = input(f"CONFIRM close {volume} lots of #{ticket} {p.symbol}? Type EXECUTE: ").strip()
        if user_confirm != 'EXECUTE':
            return "Close cancelled."
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": int(ticket),
        "symbol": p.symbol,
        "volume": volume,
        "type": close_type,
        "price": price,
        "deviation": MT5_DEFAULT_DEVIATION,
        "magic": MT5_MAGIC_NUMBER,
        "comment": MT5_COMMENT,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return f"MT5 close result: {mt5.order_send(request)}"


def _round_volume_for_symbol(symbol: str, volume: float) -> float:
    """Round a requested volume down to the broker step/min volume."""
    try:
        info = mt5.symbol_info(symbol) if mt5 else None
        step = float(getattr(info, "volume_step", 0.01) or 0.01) if info else 0.01
        min_vol = float(getattr(info, "volume_min", step) or step) if info else step
        volume = max(min_vol, float(volume))
        # floor to broker step so the request is not larger than intended
        rounded = round((volume // step) * step, 8)
        return max(min_vol, rounded)
    except Exception:
        return round(float(volume), 2)


def close_symbol_positions(symbol_text: str = "all", partial_percent: Optional[float] = None) -> str:
    """Close or partial-close open MT5 positions by symbol text.

    Examples:
    - close gold
    - close eurusd
    - close half btc
    - close all
    """
    if not stage2_enabled():
        return "Stage 2 execution is disabled. Closing trades needs MT5_STAGE2_EXECUTION_ENABLED=True."
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get() or []
    if not positions:
        return "No open MT5 positions."

    requested = (symbol_text or "all").strip()
    selected = [p for p in positions if _position_matches_symbol(p.symbol, requested)]
    if not selected:
        return f"No open positions found for {requested}."

    pct = None
    if partial_percent is not None:
        pct = max(1.0, min(float(partial_percent), 99.0))
    lines = [f"Close request: {requested}" + (f" | partial {pct}%" if pct else " | full close")]
    closed = skipped = 0
    for p in selected:
        ticket = int(p.ticket)
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        volume = float(getattr(p, "volume", 0.0) or 0.0)
        if volume <= 0:
            skipped += 1
            lines.append(f"SKIP #{ticket} {p.symbol}: zero/invalid volume.")
            continue
        if pct:
            req_volume = _round_volume_for_symbol(p.symbol, volume * pct / 100.0)
            if req_volume >= volume:
                skipped += 1
                lines.append(f"SKIP #{ticket} {p.symbol}: position too small for safe partial close.")
                continue
            res = close_position(ticket, partial_volume=req_volume, confirm=False)
            lines.append(f"PARTIAL #{ticket} {p.symbol} {side}: closed {req_volume} of {volume} lots. {res}")
        else:
            res = close_position(ticket, confirm=False)
            lines.append(f"CLOSE #{ticket} {p.symbol} {side}: {res}")
        closed += 1
    lines.append(f"Done. Actions sent: {closed}, skipped: {skipped}.")
    return "\n".join(lines)


def trail_symbol_positions(symbol_text: str = "all", lock_r: float = 0.25) -> str:
    """One-time safe trailing-stop update by symbol.

    It only trails profitable positions that already have an SL, and never loosens risk.
    For continuous trailing, use the auto manager.
    """
    if not stage2_enabled():
        return "Stage 2 execution is disabled. Trailing needs MT5_STAGE2_EXECUTION_ENABLED=True."
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get() or []
    if not positions:
        return "No open MT5 positions."

    requested = (symbol_text or "all").strip()
    selected = [p for p in positions if _position_matches_symbol(p.symbol, requested)]
    if not selected:
        return f"No open positions found for {requested}."

    lines = [f"Trailing request: {requested} | lock {lock_r}R"]
    moved = skipped = 0
    for p in selected:
        ticket = int(p.ticket)
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        entry = float(getattr(p, "price_open", 0.0) or 0.0)
        old_sl = float(getattr(p, "sl", 0.0) or 0.0)
        tp = float(getattr(p, "tp", 0.0) or 0.0)
        if entry <= 0 or old_sl <= 0:
            skipped += 1
            lines.append(f"SKIP #{ticket} {p.symbol} {side}: missing entry/SL, cannot calculate R.")
            continue
        tick = mt5.symbol_info_tick(p.symbol)
        if tick is None:
            skipped += 1
            lines.append(f"SKIP #{ticket} {p.symbol}: no live tick.")
            continue
        price = float(tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask)
        risk = abs(entry - old_sl)
        if risk <= 0:
            skipped += 1
            lines.append(f"SKIP #{ticket} {p.symbol}: invalid risk distance.")
            continue
        r_now = ((price - entry) / risk) if p.type == mt5.POSITION_TYPE_BUY else ((entry - price) / risk)
        if r_now < 1.0:
            skipped += 1
            lines.append(f"SKIP #{ticket} {p.symbol} {side}: not at +1R yet ({round(r_now, 2)}R).")
            continue
        if p.type == mt5.POSITION_TYPE_BUY:
            new_sl = max(old_sl, entry + risk * float(lock_r))
            if new_sl >= price:
                skipped += 1
                lines.append(f"SKIP #{ticket} {p.symbol}: new SL would be too close/above price.")
                continue
        else:
            new_sl = min(old_sl, entry - risk * float(lock_r))
            if new_sl <= price:
                skipped += 1
                lines.append(f"SKIP #{ticket} {p.symbol}: new SL would be too close/below price.")
                continue
        res = modify_position(ticket, sl=float(new_sl), tp=tp, confirm=False)
        moved += 1
        lines.append(f"TRAIL #{ticket} {p.symbol} {side}: SL {old_sl} -> {round(new_sl, 5)} ({round(r_now, 2)}R). {res}")
    lines.append(f"Done. Trailed: {moved}, skipped: {skipped}.")
    return "\n".join(lines)


def breakeven(ticket: int) -> str:
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return f"Position {ticket} not found."
    p = positions[0]
    return modify_position(ticket, sl=p.price_open, tp=p.tp)


def _position_matches_symbol(position_symbol: str, requested: str) -> bool:
    """Match broker symbols like XAUUSDm/BTCUSDm with user text like gold/btcusd."""
    req = (requested or '').strip()
    if not req or req.lower() in ['all', 'all profitable', 'all trades']:
        return True
    mapped = resolve_mt5_symbol(req) or map_symbol(req)
    a = _clean_symbol_text(position_symbol).replace('.', '')
    b = _clean_symbol_text(mapped).replace('.', '')
    c = _clean_symbol_text(req).replace('.', '')
    return a == b or a.startswith(b) or b.startswith(a) or a.startswith(c) or c.startswith(a)


def _is_position_profitable(p) -> bool:
    try:
        return float(getattr(p, 'profit', 0.0) or 0.0) > 0.0
    except Exception:
        return False


def _entry_sl_already_breakeven(p) -> bool:
    try:
        info = mt5.symbol_info(p.symbol) if mt5 else None
        point = float(getattr(info, 'point', 0.00001) or 0.00001) if info else 0.00001
        current_sl = float(getattr(p, 'sl', 0.0) or 0.0)
        entry = float(getattr(p, 'price_open', 0.0) or 0.0)
        return current_sl > 0 and abs(current_sl - entry) <= point * 2
    except Exception:
        return False


def breakeven_symbol(symbol_text: str = 'all') -> str:
    """Move SL to entry for profitable open positions by pair name.

    Examples:
    - breakeven gold
    - breakeven xauusdm
    - breakeven btcusd
    - breakeven all

    It only modifies profitable positions. Losing/flat trades are skipped.
    """
    if not stage2_enabled():
        return 'Stage 2 execution is disabled. Breakeven needs MT5_STAGE2_EXECUTION_ENABLED=True.'
    ok, msg = ensure_connected()
    if not ok:
        return msg
    positions = mt5.positions_get() or []
    if not positions:
        return 'No open MT5 positions.'

    requested = (symbol_text or 'all').strip()
    selected = [p for p in positions if _position_matches_symbol(p.symbol, requested)]
    if not selected:
        return f'No open positions found for {requested}.'

    lines = [f'Breakeven request: {requested}']
    moved = skipped = 0
    for p in selected:
        side = 'BUY' if p.type == mt5.POSITION_TYPE_BUY else 'SELL'
        ticket = int(p.ticket)
        profit = float(getattr(p, 'profit', 0.0) or 0.0)
        if not _is_position_profitable(p):
            skipped += 1
            lines.append(f'SKIP #{ticket} {p.symbol} {side}: not profitable yet. Profit {round(profit, 2)}')
            continue
        if _entry_sl_already_breakeven(p):
            skipped += 1
            lines.append(f'OK #{ticket} {p.symbol} {side}: already at breakeven. Entry {p.price_open}, SL {p.sl}')
            continue
        res = modify_position(ticket, sl=float(p.price_open), tp=float(p.tp), confirm=False)
        moved += 1
        lines.append(f'MOVE #{ticket} {p.symbol} {side}: SL -> entry {p.price_open}. Profit {round(profit, 2)} | {res}')
    lines.append(f'Done. Moved: {moved}, skipped: {skipped}.')
    return '\n'.join(lines)
