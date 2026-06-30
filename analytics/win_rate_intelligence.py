"""Phase 15.7 Win Rate Intelligence for Blue Forex Market AI.

This module gives Blue a single performance brain that can answer:
- win rate
- connected account win rate
- gold win rate
- take out win rate of btc
- show everything

Priority:
1) MT5 connected account closed history, if MT5 is available and connected.
2) Blue journal/demo trade records.
3) Imported/user ML dataset rows.

Read-only: this module never opens, modifies, or closes trades.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config import DATABASE_FILE
try:
    from utils.symbols import resolve_symbol
except Exception:  # pragma: no cover
    def resolve_symbol(text: str):
        return (text, text)


@dataclass
class TradeStat:
    source: str
    symbol: str
    action: str
    opened_at: str
    closed_at: str
    profit: float
    volume: float = 0.0
    result: str = "BE"
    rr: float = 0.0
    setup_type: str = "unknown"
    session: str = "unknown"
    timeframe: str = "unknown"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _clean_symbol(value: str) -> str:
    return (value or "").upper().replace("/", "").replace("-", "").replace("_", "").replace(".", "").replace(" ", "")


def _symbol_filter_text(symbol_text: Optional[str]) -> str:
    if not symbol_text:
        return ""
    text = (symbol_text or "").strip()
    if text.lower() in {"all", "everything", "account", "connected account"}:
        return ""
    name, ticker = resolve_symbol(text)
    return _clean_symbol(ticker or name or text)


def _matches_symbol(symbol: str, requested: str) -> bool:
    if not requested:
        return True
    a = _clean_symbol(symbol)
    b = _clean_symbol(requested)
    return a == b or a.startswith(b) or b.startswith(a) or b in a or a in b


def _bucket_from_profit(profit: float, eps: float = 1e-8) -> str:
    if profit > eps:
        return "WIN"
    if profit < -eps:
        return "LOSS"
    return "BE"


def _pct(num: float, den: float) -> float:
    return round((float(num) / float(den) * 100.0) if den else 0.0, 2)


def _profit_factor(gross_profit: float, gross_loss_abs: float) -> float:
    if gross_loss_abs <= 0:
        return round(gross_profit, 2) if gross_profit else 0.0
    return round(gross_profit / gross_loss_abs, 2)


def _summary(trades: List[TradeStat]) -> Dict[str, Any]:
    total = len(trades)
    wins = sum(1 for t in trades if t.result == "WIN")
    losses = sum(1 for t in trades if t.result == "LOSS")
    be = sum(1 for t in trades if t.result == "BE")
    net = round(sum(t.profit for t in trades), 2)
    gross_profit = round(sum(t.profit for t in trades if t.profit > 0), 2)
    gross_loss_abs = round(abs(sum(t.profit for t in trades if t.profit < 0)), 2)
    avg_trade = round((net / total) if total else 0.0, 2)
    avg_win = round((gross_profit / wins) if wins else 0.0, 2)
    avg_loss = round((-gross_loss_abs / losses) if losses else 0.0, 2)
    rr_values = [t.rr for t in trades if abs(t.rr) > 1e-9]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "be": be,
        "win_rate": _pct(wins, total),
        "loss_rate": _pct(losses, total),
        "be_rate": _pct(be, total),
        "net_profit": net,
        "gross_profit": gross_profit,
        "gross_loss_abs": gross_loss_abs,
        "profit_factor": _profit_factor(gross_profit, gross_loss_abs),
        "avg_trade": avg_trade,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_rr": avg_rr,
    }


def _group_lines(trades: List[TradeStat], group_attr: str, title: str, limit: int = 8) -> List[str]:
    groups: Dict[str, List[TradeStat]] = defaultdict(list)
    for t in trades:
        key = str(getattr(t, group_attr, "unknown") or "unknown")
        groups[key].append(t)
    scored = []
    for key, rows in groups.items():
        s = _summary(rows)
        scored.append((len(rows), key, s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    lines = [title]
    if not scored:
        lines.append("  no data")
        return lines
    for _, key, s in scored[:limit]:
        lines.append(
            f"  {key:<18} {s['win_rate']:>6}% | {s['wins']}W/{s['losses']}L/{s['be']}BE | net {s['net_profit']} | PF {s['profit_factor']}"
        )
    return lines


def _try_mt5():
    try:
        from mt5_bridge import terminal
        return terminal.mt5, terminal
    except Exception:
        return None, None


def _deal_dict(deal: Any) -> Dict[str, Any]:
    try:
        if hasattr(deal, "_asdict"):
            return dict(deal._asdict())
    except Exception:
        pass
    fields = [
        "ticket", "order", "time", "type", "entry", "position_id", "volume", "price",
        "commission", "swap", "profit", "fee", "symbol", "comment",
    ]
    return {f: getattr(deal, f, None) for f in fields}


def _dt_from_seconds(seconds: Any) -> str:
    try:
        return datetime.fromtimestamp(int(seconds)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _action_from_deals(mt5: Any, deals: List[Dict[str, Any]]) -> str:
    buy = getattr(mt5, "DEAL_TYPE_BUY", -999)
    sell = getattr(mt5, "DEAL_TYPE_SELL", -998)
    entry_in = getattr(mt5, "DEAL_ENTRY_IN", None)
    entry_inout = getattr(mt5, "DEAL_ENTRY_INOUT", None)

    entry_deals = [d for d in deals if d.get("entry") in {entry_in, entry_inout}]
    candidates = entry_deals or deals
    for d in candidates:
        typ = d.get("type")
        if typ == buy:
            return "BUY"
        if typ == sell:
            return "SELL"
    return "UNKNOWN"


def _mt5_account_info_text(mt5: Any) -> List[str]:
    lines: List[str] = []
    try:
        acc = mt5.account_info()
        if acc is not None:
            lines += [
                f"Account      : {getattr(acc, 'login', 'unknown')} | {getattr(acc, 'server', 'unknown')}",
                f"Balance/Equity: {round(_safe_float(getattr(acc, 'balance', 0)), 2)} / {round(_safe_float(getattr(acc, 'equity', 0)), 2)} {getattr(acc, 'currency', '')}",
                f"Margin Free  : {round(_safe_float(getattr(acc, 'margin_free', 0)), 2)} | Leverage 1:{getattr(acc, 'leverage', 'unknown')}",
            ]
    except Exception:
        pass
    return lines


def mt5_closed_trade_stats(days: int = 90, symbol_text: Optional[str] = None) -> Tuple[bool, str, List[TradeStat], List[str]]:
    """Read connected MT5 closed history and return grouped trades."""
    mt5, terminal = _try_mt5()
    if mt5 is None or terminal is None:
        return False, "MetaTrader5 package/bridge is unavailable.", [], []
    ok, msg = terminal.ensure_connected()
    if not ok:
        return False, msg, [], []

    end = datetime.now()
    start = end - timedelta(days=int(days or 90))
    try:
        deals = mt5.history_deals_get(start, end)
    except Exception as exc:
        return False, f"Could not read MT5 account history: {exc}", [], _mt5_account_info_text(mt5)
    if deals is None:
        return False, "Could not read MT5 history_deals_get(). Check terminal history and broker login.", [], _mt5_account_info_text(mt5)

    requested = _symbol_filter_text(symbol_text)
    groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for deal in deals:
        d = _deal_dict(deal)
        sym = str(d.get("symbol") or "")
        if not sym:
            # Exclude deposits, balance operations, swaps without symbol, etc.
            continue
        if requested and not _matches_symbol(sym, requested):
            continue
        key = d.get("position_id") or d.get("order") or d.get("ticket")
        groups[key].append(d)

    trades: List[TradeStat] = []
    for _, rows in groups.items():
        rows = sorted(rows, key=lambda x: int(x.get("time") or 0))
        symbol = str(rows[-1].get("symbol") or rows[0].get("symbol") or "UNKNOWN")
        profit = sum(
            _safe_float(d.get("profit"), 0.0)
            + _safe_float(d.get("commission"), 0.0)
            + _safe_float(d.get("swap"), 0.0)
            + _safe_float(d.get("fee"), 0.0)
            for d in rows
        )
        # Count only actual trade groups with buy/sell activity.
        action = _action_from_deals(mt5, rows)
        if action == "UNKNOWN":
            continue
        volume = sum(_safe_float(d.get("volume"), 0.0) for d in rows) / max(1, len(rows))
        opened_at = _dt_from_seconds(rows[0].get("time"))
        closed_at = _dt_from_seconds(rows[-1].get("time"))
        trades.append(TradeStat(
            source="MT5 connected account",
            symbol=symbol,
            action=action,
            opened_at=opened_at,
            closed_at=closed_at,
            profit=round(profit, 2),
            volume=round(volume, 4),
            result=_bucket_from_profit(profit),
        ))
    trades.sort(key=lambda t: t.closed_at, reverse=True)
    return True, msg, trades, _mt5_account_info_text(mt5)


def blue_journal_trade_stats(symbol_text: Optional[str] = None) -> List[TradeStat]:
    if not os.path.exists(DATABASE_FILE):
        return []
    requested = _symbol_filter_text(symbol_text)
    try:
        con = sqlite3.connect(DATABASE_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM journal WHERE UPPER(COALESCE(result,'')) != 'OPEN' ORDER BY id DESC").fetchall()
    except Exception:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass
    trades: List[TradeStat] = []
    for r in rows:
        sym = str(r["symbol"] or r["ticker"] or "UNKNOWN")
        if requested and not _matches_symbol(sym, requested):
            continue
        pnl = _safe_float(r["pnl"], 0.0)
        result_raw = str(r["result"] or r["outcome_label"] or "").upper()
        if result_raw in {"WIN", "TP", "PROFIT"}:
            result = "WIN"
        elif result_raw in {"LOSS", "SL"}:
            result = "LOSS"
        elif result_raw in {"BE", "BREAKEVEN"}:
            result = "BE"
        else:
            result = _bucket_from_profit(pnl)
        trades.append(TradeStat(
            source="Blue journal",
            symbol=sym,
            action=str(r["action"] or "UNKNOWN").upper(),
            opened_at=str(r["created_at"] or ""),
            closed_at=str(r["closed_at"] or r["created_at"] or ""),
            profit=round(pnl, 2),
            volume=_safe_float(r["lot_size"], 0.0),
            result=result,
            rr=_safe_float(r["rr"], _safe_float(r["rr_ratio"], 0.0)),
            setup_type=str(r["setup_type"] or "unknown"),
            session=str(r["session"] or "unknown"),
            timeframe="unknown",
        ))
    return trades


def ml_dataset_trade_stats(symbol_text: Optional[str] = None, limit: int = 50000) -> List[TradeStat]:
    if not os.path.exists(DATABASE_FILE):
        return []
    requested = _symbol_filter_text(symbol_text)
    trades: List[TradeStat] = []
    try:
        con = sqlite3.connect(DATABASE_FILE)
        rows = con.execute("SELECT payload, label FROM ml_user_dataset ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    except Exception:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass
    for payload, label in rows:
        try:
            d = json.loads(payload)
        except Exception:
            continue
        sym = str(d.get("symbol") or "UNKNOWN")
        if requested and not _matches_symbol(sym, requested):
            continue
        label_int = int(label)
        pnl = _safe_float(d.get("pnl_r"), 1.0 if label_int else -1.0)
        trades.append(TradeStat(
            source="ML dataset",
            symbol=sym,
            action=str(d.get("action") or "UNKNOWN").upper(),
            opened_at=str(d.get("timestamp") or ""),
            closed_at=str(d.get("timestamp") or ""),
            profit=round(pnl, 2),
            volume=0.0,
            result="WIN" if label_int == 1 else "LOSS",
            rr=_safe_float(d.get("pnl_r"), 0.0),
            setup_type=str(d.get("setup_type") or "unknown"),
            session=str(d.get("session") or "unknown"),
            timeframe=str(d.get("timeframe") or "unknown"),
        ))
    return trades


def _format_main_summary(title: str, trades: List[TradeStat], money_label: str = "profit") -> List[str]:
    s = _summary(trades)
    lines = [title]
    lines.append(f"Closed trades : {s['total']} | Win rate: {s['win_rate']}%")
    lines.append(f"Wins/Loss/BE  : {s['wins']} / {s['losses']} / {s['be']}")
    lines.append(f"Net {money_label:<7}: {s['net_profit']} | Gross win {s['gross_profit']} | Gross loss {s['gross_loss_abs']}")
    lines.append(f"Profit factor : {s['profit_factor']} | Avg trade {s['avg_trade']} | Avg win/loss {s['avg_win']} / {s['avg_loss']}")
    if s["avg_rr"]:
        lines.append(f"Average R     : {s['avg_rr']}R")
    return lines


def _recent_lines(trades: List[TradeStat], limit: int = 8) -> List[str]:
    lines = ["Recent closed trades"]
    if not trades:
        lines.append("  no closed trades")
        return lines
    for t in trades[:limit]:
        lines.append(
            f"  {t.closed_at[:16]:<16} {t.symbol:<12} {t.action:<4} {t.result:<4} profit {t.profit:<9} vol {t.volume}"
        )
    return lines


def win_rate_report_text(symbol_text: Optional[str] = None, days: int = 90, include_learning: bool = False) -> str:
    """Build the compact connected-account win-rate report.

    Phase 15.8 change: whenever the user asks for win rate, Blue prints only
    the connected MT5 account report in the clean terminal format requested by
    Sp. It no longer appends journal, ML dataset, directions, recent trades,
    help text, or extra sections unless a future separate command is added.
    """
    requested = (symbol_text or "").strip()
    title_symbol = f" — {requested.upper()}" if requested and requested.lower() not in {"all", "everything"} else ""
    lines = ["WIN RATE INTELLIGENCE REPORT" + title_symbol, "=" * 72]

    ok, mt5_msg, mt5_trades, account_lines = mt5_closed_trade_stats(days=days, symbol_text=symbol_text)
    lines.append("Source priority: connected MT5 account first.")
    lines.append(f"History window : last {days} days")
    if account_lines:
        lines.extend(account_lines)
    lines.append("")

    lines.append("CONNECTED ACCOUNT / MT5 HISTORY")
    if ok:
        if mt5_trades:
            summary_lines = _format_main_summary("", mt5_trades, money_label="profit")
            # _format_main_summary normally includes a title as first row. For this
            # compact report the heading is already printed above, so skip blank title.
            for row in summary_lines[1:]:
                lines.append(row)
            lines.append("")
            lines.extend(_group_lines(mt5_trades, "symbol", "Win rate by symbol"))
        else:
            lines.append(f"No closed MT5 trades found for this filter in the last {days} days.")
    else:
        lines.append("MT5 connected-account win rate unavailable.")
        lines.append("Reason: " + str(mt5_msg))

    return "\n".join(lines)

def win_rate_help_text() -> str:
    return (
        "Win Rate Commands\n"
        "  win rate                       -> connected MT5 account win-rate report\n"
        "  connected account win rate     -> same compact connected-account report\n"
        "  gold win rate                  -> gold/XAUUSD win rate from connected account\n"
        "  btc win rate                   -> BTCUSD win rate from connected account\n"
        "  take out win rate of eur       -> EURUSD win rate from connected account\n"
        "  win rate 30d                   -> last 30 days\n"
        "  win rate gold 180d             -> gold win rate from last 180 days\n"
        "Voice examples: 'hey blue show my win rate', 'hey blue take out win rate of btc'."
    )

def parse_win_rate_args(cmd: str) -> Tuple[Optional[str], int]:
    t = (cmd or "").lower().strip()
    days = 90
    import re
    m = re.search(r"(\d+)\s*(?:d|day|days)", t)
    if m:
        try:
            days = max(1, min(int(m.group(1)), 3650))
        except Exception:
            days = 90
    # Remove common words to find symbol remainder.
    cleaned = re.sub(r"\b\d+\s*(?:d|day|days)\b", " ", t)
    for phrase in [
        "connected account", "account", "show me", "show", "take out", "get", "tell me",
        "the", "my", "of", "for", "from", "last", "days", "day", "winrate", "win rate",
        "performance", "stats", "statistics", "everything", "report", "all", "history",
    ]:
        cleaned = cleaned.replace(phrase, " ")
    cleaned = re.sub(r"\d+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    symbol_text = cleaned or None
    return symbol_text, days
