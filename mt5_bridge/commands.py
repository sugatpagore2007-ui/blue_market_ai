from __future__ import annotations

import re
from typing import Optional

from utils.symbols import resolve_symbol
from risk.account import _read_float
from .terminal import (
    connect, shutdown, account_summary, positions_text, history_text, symbol_info_text,
    live_price, lot_size_from_broker, format_broker_lot, place_market_order, modify_position,
    close_position, close_symbol_positions, trail_symbol_positions, breakeven, breakeven_symbol, map_symbol, diagnose_text, symbols_text
)
from .broker_profiles import broker_status_text, set_broker_profile_text
try:
    from broker_bridge.broker_manager import active_adapter_status
except Exception:
    def active_adapter_status():
        return connect().message
try:
    from broker_bridge.ctrader_adapter import ctrader_status
except Exception:
    def ctrader_status():
        return "cTrader adapter not available."



def _extract_number_after(text: str, keys):
    for k in keys:
        m = re.search(k + r"\s*([0-9.]+)", text)
        if m:
            try: return float(m.group(1))
            except Exception: return None
    return None


def _extract_ticket(text: str) -> Optional[int]:
    m = re.search(r"(?:ticket|position|#)\s*([0-9]+)", text)
    if not m:
        m = re.search(r"\b([0-9]{5,})\b", text)
    return int(m.group(1)) if m else None


def _symbol_from_text(text: str, default='gold') -> str:
    name, ticker = resolve_symbol(text)
    if ticker:
        return ticker
    # final fallback: last word may be broker symbol
    parts = text.strip().split()
    return parts[-1].upper() if parts else default


def handle_mt5_command(cmd: str) -> Optional[str]:
    t = cmd.lower().strip()

    # Broker adapter commands: keep Forex/CFD Blue separate from Indian market project.
    if t in ['broker status', 'broker profile', 'active broker']:
        return broker_status_text()
    if t.startswith('broker set ') or t.startswith('set broker '):
        profile = t.replace('broker set ', '').replace('set broker ', '').strip()
        return set_broker_profile_text(profile)
    if t in ['connect broker', 'broker connect']:
        return active_adapter_status()
    if t in ['ctrader status', 'connect ctrader', 'broker ctrader']:
        return ctrader_status()
    if t in ['connect mt5', 'mt5 connect', 'terminal connect']:
        return connect().message
    if t in ['disconnect mt5', 'mt5 disconnect']:
        return shutdown()

    # Short/friendly MT5 commands
    if t in ['account', 'balance', 'profit', 'trades', 'open trades', 'positions']:
        return account_summary() if t in ['account', 'balance'] else positions_text()
    if t.startswith('symbols '):
        return symbols_text(t.replace('symbols ', '', 1).strip())
    if t.startswith('spec '):
        return symbol_info_text(_symbol_from_text(t.replace('spec ', '', 1).strip()))
    if t.startswith('lot '):
        sym = _symbol_from_text(t.replace('lot ', '', 1).strip())
        balance = _extract_number_after(t, ['balance', 'account']) or _read_float('Enter account balance: ', min_value=1)
        risk = _extract_number_after(t, ['risk']) or _read_float('Enter risk percent: ', min_value=0.1, max_value=5.0)
        entry = _extract_number_after(t, ['entry']) or _read_float('Enter entry price: ', min_value=0.00001)
        sl = _extract_number_after(t, ['sl', 'stop', 'stop loss']) or _read_float('Enter stop loss: ', min_value=0.00001)
        return format_broker_lot(lot_size_from_broker(sym, balance, risk, entry, sl))
    if t.startswith('trail ') or t.startswith('trailing '):
        sym = t.replace('trailing ', '', 1).replace('trail ', '', 1).strip() or 'all'
        return trail_symbol_positions(sym)
    if t.startswith('close half ') or t.startswith('half close '):
        sym = t.replace('close half ', '', 1).replace('half close ', '', 1).strip() or 'all'
        return close_symbol_positions(sym, partial_percent=50.0)
    if t.startswith('close ') and not t.startswith('close position') and not t.startswith('close trade'):
        sym = t.replace('close ', '', 1).strip() or 'all'
        return close_symbol_positions(sym)

    if t in ['mt5 diagnose', 'diagnose mt5', 'mt5 status', 'test mt5']:
        return diagnose_text()
    if t.startswith('show mt5 symbols') or t.startswith('mt5 symbols') or t.startswith('list mt5 symbols'):
        filt = t.replace('show mt5 symbols', '').replace('mt5 symbols', '').replace('list mt5 symbols', '').strip()
        return symbols_text(filt)
    if t in ['mt5 account', 'show mt5 account', 'account mt5', 'broker account', 'show account info']:
        return account_summary()
    if t in ['mt5 positions', 'show mt5 positions', 'open positions', 'show positions', 'my open trades']:
        return positions_text()
    if t.startswith('mt5 history') or 'trade history' in t:
        days = int(_extract_number_after(t, ['last', 'days']) or 7)
        return history_text(days=days)
    if 'symbol spec' in t or 'symbol specification' in t or 'broker spec' in t or 'contract size' in t or 'tick value' in t:
        sym = _symbol_from_text(t)
        return symbol_info_text(sym)
    if t.startswith('live price') or t.startswith('mt5 price') or 'live mt5 price' in t:
        sym = _symbol_from_text(t)
        return live_price(sym)
    if 'broker lot' in t or 'mt5 lot' in t or 'exact lot' in t:
        sym = _symbol_from_text(t)
        balance = _extract_number_after(t, ['balance', 'account']) or _read_float('Enter account balance: ', min_value=1)
        risk = _extract_number_after(t, ['risk']) or _read_float('Enter risk percent: ', min_value=0.1, max_value=5.0)
        entry = _extract_number_after(t, ['entry']) or _read_float('Enter entry price: ', min_value=0.00001)
        sl = _extract_number_after(t, ['sl', 'stop', 'stop loss']) or _read_float('Enter stop loss: ', min_value=0.00001)
        return format_broker_lot(lot_size_from_broker(sym, balance, risk, entry, sl))

    # Stage 2 protected commands
    if t.startswith('place ') or t.startswith('execute ') or t.startswith('buy ') or t.startswith('sell '):
        action = 'BUY' if 'buy' in t else 'SELL' if 'sell' in t else None
        if action:
            sym = _symbol_from_text(t)
            vol = _extract_number_after(t, ['lot', 'lots', 'volume']) or _read_float('Enter lot size: ', min_value=0.001)
            sl = _extract_number_after(t, ['sl', 'stop', 'stop loss']) or _read_float('Enter SL: ', min_value=0.00001)
            tp = _extract_number_after(t, ['tp', 'target', 'take profit']) or _read_float('Enter TP: ', min_value=0.00001)
            return place_market_order(sym, action, vol, sl, tp)
    if 'breakeven' in t or 'break even' in t or t.startswith('be '):
        # New natural command support:
        # breakeven btcusd / breakeven ethusd / breakeven eurusd / breakeven gold / breakeven all
        ticket = _extract_ticket(t)
        if ticket:
            return breakeven(ticket)
        cleaned = (t.replace('break even', 'breakeven')
                     .replace('breakeven', '')
                     .replace('move sl to entry', '')
                     .replace('move stop to entry', '')
                     .replace('sl at entry', '')
                     .replace('be ', '')
                     .strip())
        if not cleaned:
            cleaned = 'all'
        return breakeven_symbol(cleaned)
    if t.startswith('modify position') or t.startswith('modify trade') or 'change sl' in t or 'change tp' in t:
        ticket = _extract_ticket(t) or int(_read_float('Enter position ticket: ', min_value=1))
        sl = _extract_number_after(t, ['sl', 'stop'])
        tp = _extract_number_after(t, ['tp', 'target'])
        if sl is None and tp is None:
            sl = _read_float('Enter new SL: ', min_value=0.00001)
            tp = _read_float('Enter new TP: ', min_value=0.00001)
        return modify_position(ticket, sl=sl, tp=tp)
    if t.startswith('close position') or t.startswith('close trade') or 'partial close' in t:
        ticket = _extract_ticket(t) or int(_read_float('Enter position ticket: ', min_value=1))
        vol = _extract_number_after(t, ['lot', 'lots', 'volume']) if 'partial' in t else None
        return close_position(ticket, partial_volume=vol)
    return None
