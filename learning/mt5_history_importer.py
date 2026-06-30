"""Phase 15 MT5 history importer for Blue Forex Market AI.

Reads closed deals from the already-open MT5 terminal, reconstructs basic
features around each entry, exports a Blue-compatible ML CSV, imports it into
Phase 11 dataset storage, and optionally retrains the dataset model.

This module is read-only. It never places or modifies orders.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    from config import PHASE15_DATASET_DIR, PHASE15_DEFAULT_HISTORY_TIMEFRAME
except Exception:
    PHASE15_DATASET_DIR = "datasets"
    PHASE15_DEFAULT_HISTORY_TIMEFRAME = "5m"

from learning.trade_labeler import default_ml_row, infer_action, norm_symbol, safe_float, session_from_time
from learning.auto_history_learning import maybe_auto_retrain, update_status, filter_new_learning_rows
from learning.dataset_learning import import_dataset_to_db, train_dataset_model


def _mt5_module():
    try:
        from mt5_bridge import terminal
        return terminal.mt5, terminal
    except Exception:
        return None, None


def _timeframe_constant(mt5: Any, timeframe: str):
    tf = (timeframe or "5m").lower().strip()
    mapping = {
        "1m": "TIMEFRAME_M1", "3m": "TIMEFRAME_M3", "5m": "TIMEFRAME_M5", "15m": "TIMEFRAME_M15",
        "30m": "TIMEFRAME_M30", "1h": "TIMEFRAME_H1", "4h": "TIMEFRAME_H4", "1d": "TIMEFRAME_D1", "daily": "TIMEFRAME_D1",
    }
    return getattr(mt5, mapping.get(tf, "TIMEFRAME_M5"), getattr(mt5, "TIMEFRAME_M5", 5))


def _deal_dict(deal: Any) -> Dict[str, Any]:
    try:
        if hasattr(deal, "_asdict"):
            return dict(deal._asdict())
    except Exception:
        pass
    fields = [
        "ticket", "order", "time", "time_msc", "type", "entry", "magic", "position_id", "reason",
        "volume", "price", "commission", "swap", "profit", "fee", "symbol", "comment", "external_id",
    ]
    return {f: getattr(deal, f, None) for f in fields}


def _dt_from_mt5_seconds(seconds: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(seconds))
    except Exception:
        return datetime.now()


def _deal_is_entry(mt5: Any, d: Dict[str, Any]) -> bool:
    entry = d.get("entry")
    if entry == getattr(mt5, "DEAL_ENTRY_IN", object()):
        return True
    if entry == getattr(mt5, "DEAL_ENTRY_INOUT", object()):
        return True
    # Fallback: opening deals often have near-zero profit.
    typ = d.get("type")
    return typ in {getattr(mt5, "DEAL_TYPE_BUY", -999), getattr(mt5, "DEAL_TYPE_SELL", -998)} and abs(safe_float(d.get("profit"), 0)) < 1e-9


def _deal_is_exit(mt5: Any, d: Dict[str, Any]) -> bool:
    entry = d.get("entry")
    if entry in {getattr(mt5, "DEAL_ENTRY_OUT", object()), getattr(mt5, "DEAL_ENTRY_OUT_BY", object())}:
        return True
    return abs(safe_float(d.get("profit"), 0)) > 1e-9


def _action_from_deal_type(mt5: Any, typ: Any) -> str:
    if typ == getattr(mt5, "DEAL_TYPE_BUY", -999):
        return "BUY"
    if typ == getattr(mt5, "DEAL_TYPE_SELL", -998):
        return "SELL"
    return infer_action(typ)


def _fetch_context_features(mt5: Any, terminal: Any, symbol: str, entry_dt: datetime, timeframe: str) -> Dict[str, Any]:
    """Reconstruct lightweight market/candle features around a historical entry."""
    features: Dict[str, Any] = {
        "market_regime": "unknown",
        "trend_bias": "neutral",
        "atr": 0.0,
        "spread_pips": 0.0,
        "candlestick_bias": "neutral",
        "candlestick_pattern": "unknown",
        "candlestick_strength": 0.0,
        "candlestick_pattern_count": 0,
        "talib_available": False,
        "talib_patterns_detected": 0,
    }
    try:
        resolved = terminal.resolve_mt5_symbol(symbol) or symbol
        mt5.symbol_select(resolved, True)
        tf_const = _timeframe_constant(mt5, timeframe)
        start = entry_dt - timedelta(days=5)
        end = entry_dt + timedelta(minutes=5)
        rates = mt5.copy_rates_range(resolved, tf_const, start, end)
        if rates is None or len(rates) < 30 or pd is None:
            return features
        df = pd.DataFrame(rates)
        # MT5 columns: time, open, high, low, close, tick_volume, spread, real_volume.
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        if "spread" in df.columns and len(df):
            features["spread_pips"] = float(df.iloc[-1].get("spread", 0) or 0)
        close = df["close"]
        sma20 = close.tail(20).mean()
        sma50 = close.tail(min(50, len(close))).mean()
        if sma20 > sma50 * 1.0002:
            features["market_regime"] = "bullish"
            features["trend_bias"] = "bullish"
        elif sma20 < sma50 * 0.9998:
            features["market_regime"] = "bearish"
            features["trend_bias"] = "bearish"
        else:
            features["market_regime"] = "sideways"
            features["trend_bias"] = "neutral"
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features["atr"] = round(float(tr.tail(14).mean() or 0), 6)
        try:
            from analysis.candlestick_patterns import detect_candlestick_patterns
            candle = detect_candlestick_patterns(df.tail(80), lookback=5)
            top = candle.get("top_patterns") or []
            first = top[0] if top else {}
            features.update({
                "candlestick_bias": candle.get("bias", "neutral"),
                "candlestick_pattern": str(first.get("name") or "unknown").lower().replace(" ", "_"),
                "candlestick_strength": safe_float(first.get("strength"), 0.0),
                "candlestick_pattern_count": len(top),
                "talib_available": bool(candle.get("talib_available")),
                "talib_patterns_detected": safe_float(candle.get("talib_patterns_detected"), 0.0),
            })
        except Exception:
            pass
    except Exception:
        return features
    return features


def _group_deals_to_trades(mt5: Any, deals: Iterable[Any], timeframe: str, reconstruct: bool = True) -> List[Dict[str, Any]]:
    groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for deal in deals:
        d = _deal_dict(deal)
        key = d.get("position_id") or d.get("order") or d.get("ticket")
        groups[key].append(d)

    _, terminal = _mt5_module()
    rows: List[Dict[str, Any]] = []
    for position_id, items in groups.items():
        items = sorted(items, key=lambda x: int(x.get("time") or 0))
        entry_deals = [d for d in items if _deal_is_entry(mt5, d)]
        exit_deals = [d for d in items if _deal_is_exit(mt5, d)]
        if not exit_deals:
            continue
        entry = entry_deals[0] if entry_deals else items[0]
        symbol = str(entry.get("symbol") or exit_deals[-1].get("symbol") or "UNKNOWN")
        action = _action_from_deal_type(mt5, entry.get("type"))
        if action not in {"BUY", "SELL"}:
            # Closing deal type can be opposite, so only use it as last fallback.
            action = _action_from_deal_type(mt5, items[0].get("type"))
        entry_time = _dt_from_mt5_seconds(entry.get("time"))
        exit_time = _dt_from_mt5_seconds(exit_deals[-1].get("time"))
        entry_price = safe_float(entry.get("price"), 0.0)
        exit_price = safe_float(exit_deals[-1].get("price"), 0.0)
        profit = sum(safe_float(d.get("profit"), 0.0) + safe_float(d.get("commission"), 0.0) + safe_float(d.get("swap"), 0.0) + safe_float(d.get("fee"), 0.0) for d in items)
        volume = sum(safe_float(d.get("volume"), 0.0) for d in entry_deals) or safe_float(entry.get("volume"), 0.0)
        context = {}
        if reconstruct and terminal is not None:
            context = _fetch_context_features(mt5, terminal, symbol, entry_time, timeframe)
        setup_type = "mt5_history_reconstructed"
        comment_text = " ".join(str(d.get("comment") or "") for d in items).lower()
        if "blue" in comment_text:
            setup_type = "blue_mt5_history"
        row = default_ml_row(
            timestamp=entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            symbol=norm_symbol(symbol),
            timeframe=timeframe,
            action=action,
            setup_type=setup_type,
            session=session_from_time(entry_time),
            entry=entry_price,
            exit_price=exit_price,
            profit=profit,
            pnl=profit,
            source="mt5_history",
            source_knowledge="mt5_history_auto_import",
            notes=f"Phase 15 MT5 import. Broker symbol={symbol}, position_id={position_id}, exit={exit_time}, volume={volume}, profit={round(profit, 2)}. Setup reconstructed from candles where possible.",
            **context,
        )
        # Skip exact breakeven rows because Phase 11 binary classifier needs win/loss.
        if row["result"] in {"win", "loss"}:
            rows.append(row)
    return rows


def export_rows_to_csv(rows: List[Dict[str, Any]], prefix: str = "mt5_history_learning") -> str:
    os.makedirs(PHASE15_DATASET_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(PHASE15_DATASET_DIR, f"{prefix}_{stamp}.csv")
    if not rows:
        # still write a header file for clarity
        rows = [default_ml_row(symbol="UNKNOWN", action="WAIT", result="breakeven", notes="No rows imported")]
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return path


def learn_mt5_history(days: int = 30, timeframe: str = PHASE15_DEFAULT_HISTORY_TIMEFRAME, train_after: bool = True, reconstruct: bool = True) -> Dict[str, Any]:
    mt5, terminal = _mt5_module()
    if mt5 is None or terminal is None:
        return {"ok": False, "message": "MetaTrader5 bridge is unavailable. Install with: pip install MetaTrader5"}
    ok, msg = terminal.ensure_connected()
    if not ok:
        return {"ok": False, "message": msg}
    end = datetime.now()
    start = end - timedelta(days=int(days or 30))
    deals = mt5.history_deals_get(start, end)
    if deals is None:
        return {"ok": False, "message": "Could not read MT5 history_deals_get(). Check MT5 terminal history range and login."}
    rows_all = _group_deals_to_trades(mt5, deals, timeframe=timeframe, reconstruct=reconstruct)
    rows, skipped_duplicates = filter_new_learning_rows(rows_all, source_hint="mt5_history")
    csv_path = export_rows_to_csv(rows, prefix=f"mt5_history_{int(days or 30)}d")
    imported = {"imported_rows": 0}
    train_result = None
    if rows:
        imported = import_dataset_to_db(csv_path)
        if train_after:
            # Retrain immediately when enough rows exist; otherwise maybe_auto_retrain explains why not.
            auto = maybe_auto_retrain(new_rows=len(rows))
            if auto.get("ok"):
                train_result = auto
            else:
                train_result = train_dataset_model(path=None, use_imported=True)
    update_status(last_mt5_import={
        "days": days,
        "timeframe": timeframe,
        "csv_path": csv_path,
        "rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "deals_read": len(deals),
        "imported_rows": imported.get("imported_rows", 0),
        "trained": bool(train_result and train_result.get("ok")),
        "trained_message": (train_result or {}).get("message") if train_result else "training skipped",
        "at": datetime.utcnow().isoformat(),
    })
    return {
        "ok": True,
        "message": f"MT5 history learning finished: read {len(deals)} deals, built {len(rows_all)} labeled trade rows, skipped {skipped_duplicates} duplicates, saved {csv_path}, imported {imported.get('imported_rows', 0)} new rows.",
        "deals_read": len(deals),
        "rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "csv_path": csv_path,
        "imported_rows": imported.get("imported_rows", 0),
        "train_result": train_result,
    }


def mt5_history_learning_help() -> str:
    return (
        "Phase 15 MT5 History Learning Commands\n"
        "mt5 learn history 30d        Read last 30 days closed MT5 trades and train/import\n"
        "mt5 learn history 90d        Read last 90 days\n"
        "mt5 learn history all        Uses 3650 days as a practical full-history window\n"
        "mt5 learn history 30d 15m    Reconstruct candle features using 15m candles\n\n"
        "This is read-only. It uses MT5 history_deals_get, exports a CSV in datasets/, imports rows into Blue ML, then retrains when enough win/loss rows exist.\n"
        "Best data quality: trades created by Blue have the richest notes; manual MT5 trades are reconstructed from historical candles and profit/loss."
    )
