"""Broker symbol intelligence report.

Helps Blue adapt to Exness/XM/IC/Pepperstone/other MT5 symbol naming instead
of assuming one broker's suffix.
"""
from __future__ import annotations

from typing import List

WATCHLIST = ["xauusd", "xagusd", "ethusd", "btcusd", "usoil", "usdjpy", "eurusd", "ustec", "gbpusd"]

def broker_symbol_intelligence_report() -> str:
    try:
        from utils.symbols import resolve_symbol
        from mt5_bridge.terminal import ensure_connected, resolve_mt5_symbol, symbol_info_text
        from mt5_bridge.broker_profiles import broker_status_text
    except Exception as exc:
        return f"Broker intelligence unavailable: {exc}"

    ok, msg = ensure_connected()
    lines: List[str] = ["Broker Intelligence Brain", broker_status_text(), ""]
    if not ok:
        lines.append(msg)
        lines.append("Open your broker MT5 terminal manually, log in, then run: connect mt5")
        return "\n".join(lines)

    lines.append("Detected symbol mapping:")
    for name in WATCHLIST:
        display, ticker = resolve_symbol(name)
        if not ticker:
            continue
        try:
            mt5_symbol = resolve_mt5_symbol(ticker)
            lines.append(f"{display:10s} | Blue={ticker:10s} -> Broker={mt5_symbol}")
        except Exception as exc:
            lines.append(f"{name:10s} | mapping error: {exc}")
    lines.append("")
    lines.append("Tip: If any broker symbol looks wrong, run 'show mt5 symbols xau/eur/btc' and update broker profile aliases.")
    return "\n".join(lines)
