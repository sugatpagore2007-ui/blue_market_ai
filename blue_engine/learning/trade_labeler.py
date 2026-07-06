"""Phase 15 trade labeling utilities.

Converts raw demo/MT5/backtest trades into the same labeled rows that Blue's
Phase 11 dataset learner already understands. This module is deliberately
read-only and safe: it prepares learning data; it never places orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def norm_symbol(value: Any) -> str:
    s = str(value or "").upper().replace("/", "").replace("-", "").replace("_", "").replace(".", "").strip()
    if "GOLD" in s or "XAU" in s:
        return "XAUUSD"
    if "SILVER" in s or "XAG" in s:
        return "XAGUSD"
    if "BTC" in s:
        return "BTCUSD"
    if "ETH" in s:
        return "ETHUSD"
    if "EUR" in s and "USD" in s:
        return "EURUSD"
    if "GBP" in s and "USD" in s:
        return "GBPUSD"
    if "USD" in s and "JPY" in s:
        return "USDJPY"
    if "JPY" in s and len(s) <= 8:
        return "USDJPY"
    if "OIL" in s or "WTI" in s or "XTI" in s:
        return "USOIL"
    if "NAS" in s or "USTEC" in s or "NQ" in s:
        return "NAS100"
    if "US500" in s or "SPX" in s or "ES" == s[:2]:
        return "US500"
    return s[:18] or "UNKNOWN"


def parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if value is None or value == "":
        return None
    # MT5 sometimes gives POSIX seconds.
    try:
        if isinstance(value, (int, float)) or str(value).strip().isdigit():
            v = float(value)
            if v > 10_000:
                return datetime.fromtimestamp(v)
    except Exception:
        pass
    text = str(value).strip().replace("T", " ").replace("Z", "")
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def session_from_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
    hour = dt.hour
    # Simple broker-time/session buckets. Good enough for ML features; user can refine later.
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 12:
        return "london"
    if 12 <= hour < 17:
        return "london_new_york_overlap"
    if 17 <= hour < 22:
        return "new_york"
    return "rollover"


def label_from_profit(profit: Any, result: Any = None) -> Optional[int]:
    p = safe_float(profit, 0.0)
    if p > 0:
        return 1
    if p < 0:
        return 0
    text = str(result or "").strip().lower()
    if text in {"win", "won", "profit", "tp", "target", "green", "1"}:
        return 1
    if text in {"loss", "lost", "sl", "stop", "red", "0"}:
        return 0
    if any(x in text for x in ["win", "profit", "tp"]):
        return 1
    if any(x in text for x in ["loss", "lost", "sl", "stop"]):
        return 0
    return None


def result_text(label: Optional[int], profit: float) -> str:
    if label == 1:
        return "win"
    if label == 0:
        return "loss"
    if abs(profit) < 1e-9:
        return "breakeven"
    return "unknown"


def infer_action(value: Any) -> str:
    text = str(value or "").upper().strip()
    if text in {"0", "BUY", "LONG", "B"} or "BUY" in text or "LONG" in text:
        return "BUY"
    if text in {"1", "SELL", "SHORT", "S"} or "SELL" in text or "SHORT" in text:
        return "SELL"
    return "WAIT"


def infer_market_regime_from_prices(open_price: Any, close_price: Any, action: str) -> str:
    o = safe_float(open_price, 0.0)
    c = safe_float(close_price, 0.0)
    if o and c:
        pct = (c - o) / o if o else 0
        if pct > 0.001:
            return "bullish"
        if pct < -0.001:
            return "bearish"
        return "sideways"
    if action == "BUY":
        return "bullish_or_reversal"
    if action == "SELL":
        return "bearish_or_reversal"
    return "unknown"


def rr_from_prices(entry: Any, sl: Any, tp: Any, action: str = "BUY") -> float:
    e = safe_float(entry, 0.0)
    s = safe_float(sl, 0.0)
    t = safe_float(tp, 0.0)
    if e and s and t:
        risk = abs(e - s)
        reward = abs(t - e)
        return round(reward / risk, 3) if risk > 0 else 0.0
    return 0.0


def r_multiple_from_trade(entry: Any, sl: Any, exit_price: Any, action: str, profit: Any = None) -> float:
    e = safe_float(entry, 0.0)
    s = safe_float(sl, 0.0)
    x = safe_float(exit_price, 0.0)
    if e and s and x and abs(e - s) > 0:
        risk = abs(e - s)
        if action == "BUY":
            return round((x - e) / risk, 3)
        if action == "SELL":
            return round((e - x) / risk, 3)
    # If stop loss is missing, use sign-only pseudo-R. This is enough for label training,
    # but users should provide SL/backtest risk for stronger ML.
    p = safe_float(profit, 0.0)
    if p > 0:
        return 1.0
    if p < 0:
        return -1.0
    return 0.0


def default_ml_row(**kwargs: Any) -> Dict[str, Any]:
    """Return a complete row matching Phase 11/14 dataset columns."""
    timestamp = kwargs.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry_dt = parse_datetime(timestamp)
    symbol = kwargs.get("symbol") or "UNKNOWN"
    action = infer_action(kwargs.get("action"))
    profit = safe_float(kwargs.get("profit") if kwargs.get("profit") is not None else kwargs.get("pnl"), 0.0)
    label = label_from_profit(profit, kwargs.get("result"))
    result = result_text(label, profit)
    pnl_r = safe_float(kwargs.get("pnl_r"), 0.0)
    if not pnl_r:
        pnl_r = r_multiple_from_trade(kwargs.get("entry"), kwargs.get("stop_loss"), kwargs.get("exit_price"), action, profit)
    rr = safe_float(kwargs.get("rr_ratio"), 0.0) or rr_from_prices(kwargs.get("entry"), kwargs.get("stop_loss"), kwargs.get("target_2") or kwargs.get("take_profit"), action)
    return {
        "timestamp": str(timestamp),
        "symbol": str(symbol),
        "timeframe": str(kwargs.get("timeframe") or "5m"),
        "action": action,
        "setup_type": str(kwargs.get("setup_type") or "history_reconstructed").lower(),
        "trade_style": str(kwargs.get("trade_style") or "intraday").lower(),
        "session": str(kwargs.get("session") or session_from_time(entry_dt)).lower(),
        "market_regime": str(kwargs.get("market_regime") or infer_market_regime_from_prices(kwargs.get("entry"), kwargs.get("exit_price"), action)).lower(),
        "trend_bias": str(kwargs.get("trend_bias") or ("bullish" if action == "BUY" else "bearish" if action == "SELL" else "neutral")).lower(),
        "news_risk": str(kwargs.get("news_risk") or "unknown").lower(),
        "spread_pips": safe_float(kwargs.get("spread_pips"), 0.0),
        "atr": safe_float(kwargs.get("atr") if kwargs.get("atr") is not None else kwargs.get("atr_pips"), 0.0),
        "rr_ratio": rr,
        "rule_confidence": safe_float(kwargs.get("rule_confidence"), 50.0),
        "tf_alignment": safe_float(kwargs.get("tf_alignment"), 0.0),
        "liquidity_sweep": int(safe_float(kwargs.get("liquidity_sweep"), 0.0) > 0),
        "fvg_present": int(safe_float(kwargs.get("fvg_present"), 0.0) > 0),
        "order_block_present": int(safe_float(kwargs.get("order_block_present"), 0.0) > 0),
        "smt_divergence": int(safe_float(kwargs.get("smt_divergence"), 0.0) > 0),
        "correlation_risk": safe_float(kwargs.get("correlation_risk"), 0.0),
        "entry": safe_float(kwargs.get("entry"), 0.0),
        "stop_loss": safe_float(kwargs.get("stop_loss"), 0.0),
        "target_1": safe_float(kwargs.get("target_1"), 0.0),
        "target_2": safe_float(kwargs.get("target_2") or kwargs.get("take_profit"), 0.0),
        "candlestick_bias": str(kwargs.get("candlestick_bias") or "neutral").lower(),
        "candlestick_pattern": str(kwargs.get("candlestick_pattern") or "unknown").lower().replace(" ", "_"),
        "candlestick_strength": safe_float(kwargs.get("candlestick_strength"), 0.0),
        "candlestick_pattern_count": safe_float(kwargs.get("candlestick_pattern_count"), 0.0),
        "talib_available": str(kwargs.get("talib_available") if kwargs.get("talib_available") is not None else False).lower(),
        "talib_patterns_detected": safe_float(kwargs.get("talib_patterns_detected"), 0.0),
        "source_knowledge": str(kwargs.get("source_knowledge") or kwargs.get("source") or "phase15_auto_history"),
        "result": result,
        "pnl_r": pnl_r,
        "notes": str(kwargs.get("notes") or "Auto-generated by Phase 15 history/backtest learning."),
    }
