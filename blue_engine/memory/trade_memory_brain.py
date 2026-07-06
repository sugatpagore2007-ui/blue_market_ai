"""Trade memory and setup performance layer.

Blue uses this for human-like experience: it remembers which symbols, sessions,
setup types and regimes have worked or failed in the journal.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

try:
    from config import DATABASE_FILE, TRADE_MEMORY_MIN_SAMPLE, TRADE_MEMORY_CONFIDENCE_STEP
except Exception:
    DATABASE_FILE = "blue_market_ai.db"
    TRADE_MEMORY_MIN_SAMPLE = 5
    TRADE_MEMORY_CONFIDENCE_STEP = 4

WIN_RESULTS = {"WIN", "TP", "PROFIT"}
LOSS_RESULTS = {"LOSS", "SL"}

def _connect():
    return sqlite3.connect(DATABASE_FILE)

def _rows(query: str, args: tuple = ()) -> List[sqlite3.Row]:
    con = _connect(); con.row_factory = sqlite3.Row
    try:
        return list(con.execute(query, args).fetchall())
    except Exception:
        return []
    finally:
        con.close()

def _stats(rows: List[sqlite3.Row]) -> Dict[str, Any]:
    total = len(rows)
    wins = sum(1 for r in rows if str(r["result"]).upper() in WIN_RESULTS)
    losses = sum(1 for r in rows if str(r["result"]).upper() in LOSS_RESULTS)
    pnl = round(sum(float(r["pnl"] or 0) for r in rows), 2)
    return {
        "sample": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / total * 100) if total else 0, 2),
        "net_pnl": pnl,
    }

def infer_setup_type(signal: Dict[str, Any]) -> str:
    text = " ".join([
        str(signal.get("analyst_reason", "")),
        str(signal.get("regime", "")),
        str(signal.get("human_read", "")),
    ]).lower()
    if "liquidity sweep" in text or "sweep" in text:
        return "liquidity_sweep_reversal"
    if "fvg" in text or "fair value" in text:
        return "fvg_retest"
    if "order block" in text or "ob" in text:
        return "order_block_retest"
    if "breakout" in text or "bos" in text:
        return "structure_breakout"
    if "ema" in text or "trend" in text:
        return "trend_continuation"
    return "general_confluence"

def memory_snapshot_for_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    symbol = signal.get("symbol")
    action = signal.get("action")
    setup_type = signal.get("setup_type") or infer_setup_type(signal)
    session = signal.get("session") or "unknown"
    regime = signal.get("regime") or "unknown"

    symbol_rows = _rows("SELECT * FROM journal WHERE result!='OPEN' AND symbol=?", (symbol,)) if symbol else []
    setup_rows = _rows("SELECT * FROM journal WHERE result!='OPEN' AND setup_type=?", (setup_type,))
    session_rows = _rows("SELECT * FROM journal WHERE result!='OPEN' AND session=?", (session,))
    regime_rows = _rows("SELECT * FROM journal WHERE result!='OPEN' AND market_regime=?", (regime,))
    action_rows = _rows("SELECT * FROM journal WHERE result!='OPEN' AND symbol=? AND action=?", (symbol, action)) if symbol and action else []

    symbol_stats = _stats(symbol_rows)
    setup_stats = _stats(setup_rows)
    session_stats = _stats(session_rows)
    regime_stats = _stats(regime_rows)
    action_stats = _stats(action_rows)

    notes = []
    for label, st in [("symbol", symbol_stats), ("setup", setup_stats), ("session", session_stats), ("regime", regime_stats)]:
        if st["sample"] >= TRADE_MEMORY_MIN_SAMPLE:
            notes.append(f"{label} memory: {st['sample']} trades, {st['win_rate']}% win rate, net PnL {st['net_pnl']}.")
    if not notes:
        notes.append("Not enough closed journal history yet; Blue will learn more after you update trade outcomes.")

    adjustment = 0
    trusted = [st for st in (symbol_stats, setup_stats, session_stats, regime_stats, action_stats) if st["sample"] >= TRADE_MEMORY_MIN_SAMPLE]
    if trusted:
        avg_wr = sum(st["win_rate"] for st in trusted) / len(trusted)
        if avg_wr >= 60:
            adjustment = TRADE_MEMORY_CONFIDENCE_STEP
        elif avg_wr <= 42:
            adjustment = -TRADE_MEMORY_CONFIDENCE_STEP

    return {
        "setup_type": setup_type,
        "symbol_stats": symbol_stats,
        "setup_stats": setup_stats,
        "session_stats": session_stats,
        "regime_stats": regime_stats,
        "action_stats": action_stats,
        "confidence_adjustment": adjustment,
        "note": " ".join(notes),
    }

def trade_memory_report(limit: int = 8) -> str:
    rows = _rows("SELECT * FROM journal WHERE result!='OPEN' ORDER BY closed_at DESC, id DESC LIMIT ?", (int(limit),))
    all_rows = _rows("SELECT * FROM journal WHERE result!='OPEN'")
    overall = _stats(all_rows)
    lines = [
        "Trade Memory Brain",
        f"Closed trades: {overall['sample']} | Wins: {overall['wins']} | Losses: {overall['losses']} | Win rate: {overall['win_rate']}% | Net PnL: {overall['net_pnl']}",
        "",
        "Recent closed memory:"
    ]
    if not rows:
        lines.append("No closed trades yet. Use 'close trade' after paper/demo trades so Blue can learn.")
    for r in rows:
        lines.append(f"#{r['id']} {r['symbol']} {r['action']} {r['result']} | setup={r['setup_type'] or 'unknown'} | session={r['session'] or 'unknown'} | rr={r['rr'] or 0} | pnl={r['pnl'] or 0}")
    return "\n".join(lines)
