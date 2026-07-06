"""Phase 15 backtest report importer for Blue Forex Market AI.

Accepts common Strategy Tester / TradingView / manual backtest CSV exports,
normalizes columns, exports a Blue-compatible ML dataset, imports it, and can
retrain the Phase 11 dataset model.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    from config import PHASE15_DATASET_DIR, PHASE15_REPORTS_DIR
except Exception:
    PHASE15_DATASET_DIR = "datasets"
    PHASE15_REPORTS_DIR = "reports"

from learning.trade_labeler import default_ml_row, infer_action, norm_symbol, parse_datetime, safe_float, session_from_time
from learning.dataset_learning import import_dataset_to_db, train_dataset_model
from learning.auto_history_learning import maybe_auto_retrain, update_status, filter_new_learning_rows

ALIASES = {
    "symbol": ["symbol", "pair", "instrument", "market", "ticker"],
    "action": ["action", "side", "type", "direction", "order_type", "trade_type"],
    "entry_time": ["entry_time", "open_time", "time", "date", "opened", "open_date", "entry date/time", "entry_time_utc"],
    "exit_time": ["exit_time", "close_time", "closed", "close_date", "exit date/time", "exit_time_utc"],
    "entry": ["entry", "entry_price", "open_price", "price", "avg_entry_price"],
    "exit_price": ["exit", "exit_price", "close_price", "avg_exit_price"],
    "stop_loss": ["stop_loss", "sl", "stop", "stop_price"],
    "target_1": ["target_1", "tp1", "take_profit_1"],
    "target_2": ["target_2", "tp2", "take_profit", "tp", "take_profit_2"],
    "profit": ["profit", "pnl", "net_profit", "gross_profit", "net_pnl", "pl", "profit_loss"],
    "pnl_r": ["pnl_r", "r", "r_multiple", "r_result", "profit_r", "rr_result"],
    "result": ["result", "outcome", "win_loss", "status"],
    "timeframe": ["timeframe", "tf", "chart_tf"],
    "setup_type": ["setup_type", "setup", "strategy", "pattern", "entry_model"],
    "session": ["session", "market_session"],
    "market_regime": ["market_regime", "regime", "market_context"],
    "news_risk": ["news_risk", "news", "impact"],
    "spread_pips": ["spread_pips", "spread"],
    "atr": ["atr", "atr_pips", "volatility"],
    "rr_ratio": ["rr_ratio", "rr", "risk_reward", "reward_risk"],
    "rule_confidence": ["rule_confidence", "confidence", "score", "probability"],
    "tf_alignment": ["tf_alignment", "timeframe_alignment", "mft_alignment", "mtf_alignment"],
    "liquidity_sweep": ["liquidity_sweep", "sweep"],
    "fvg_present": ["fvg_present", "fvg"],
    "order_block_present": ["order_block_present", "order_block", "ob"],
    "candlestick_pattern": ["candlestick_pattern", "candle_pattern", "pattern_name"],
    "candlestick_bias": ["candlestick_bias", "candle_bias"],
    "candlestick_strength": ["candlestick_strength", "candle_strength"],
}


def _clean_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
    return df


def _get(row: Any, canonical: str, default: Any = "") -> Any:
    aliases = ALIASES.get(canonical, [canonical])
    for col in aliases:
        c = str(col).strip().lower().replace(" ", "_").replace("/", "_")
        try:
            value = row.get(c, None)
        except Exception:
            value = None
        if value is not None and str(value).strip() != "" and str(value).strip().lower() != "nan":
            return value
    return default


def normalize_backtest_csv(path: str, default_timeframe: str = "5m") -> List[Dict[str, Any]]:
    if pd is None:
        raise RuntimeError("pandas is not installed. Run: pip install pandas")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Backtest file not found: {path}")
    df = _clean_columns(pd.read_csv(path))
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        symbol = norm_symbol(_get(r, "symbol", "UNKNOWN"))
        action = infer_action(_get(r, "action", "WAIT"))
        entry_time_raw = _get(r, "entry_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        entry_dt = parse_datetime(entry_time_raw)
        timestamp = entry_dt.strftime("%Y-%m-%d %H:%M:%S") if entry_dt else str(entry_time_raw)
        profit = safe_float(_get(r, "profit", 0.0), 0.0)
        pnl_r = safe_float(_get(r, "pnl_r", 0.0), 0.0)
        result = _get(r, "result", "")
        # Convert common Strategy Tester sell/buy numeric types.
        if action == "WAIT":
            typ = str(_get(r, "action", "")).lower()
            if typ in {"0", "buy", "long"}:
                action = "BUY"
            elif typ in {"1", "sell", "short"}:
                action = "SELL"
        row = default_ml_row(
            timestamp=timestamp,
            symbol=symbol,
            timeframe=str(_get(r, "timeframe", default_timeframe) or default_timeframe),
            action=action,
            setup_type=str(_get(r, "setup_type", "backtest_imported")),
            session=str(_get(r, "session", session_from_time(entry_dt))),
            market_regime=str(_get(r, "market_regime", "unknown")),
            news_risk=str(_get(r, "news_risk", "unknown")),
            spread_pips=_get(r, "spread_pips", 0.0),
            atr=_get(r, "atr", 0.0),
            rr_ratio=_get(r, "rr_ratio", 0.0),
            rule_confidence=_get(r, "rule_confidence", 50.0),
            tf_alignment=_get(r, "tf_alignment", 0.0),
            liquidity_sweep=_get(r, "liquidity_sweep", 0),
            fvg_present=_get(r, "fvg_present", 0),
            order_block_present=_get(r, "order_block_present", 0),
            candlestick_pattern=_get(r, "candlestick_pattern", "unknown"),
            candlestick_bias=_get(r, "candlestick_bias", "neutral"),
            candlestick_strength=_get(r, "candlestick_strength", 0.0),
            entry=_get(r, "entry", 0.0),
            stop_loss=_get(r, "stop_loss", 0.0),
            target_1=_get(r, "target_1", 0.0),
            target_2=_get(r, "target_2", 0.0),
            exit_price=_get(r, "exit_price", 0.0),
            profit=profit,
            pnl_r=pnl_r,
            result=result,
            source="backtest_report",
            source_knowledge="phase15_backtest_import",
            notes=f"Phase 15 backtest import from {os.path.basename(path)}. Exit time={_get(r, 'exit_time', '')}",
        )
        if row["result"] in {"win", "loss"}:
            rows.append(row)
    return rows


def export_backtest_rows(rows: List[Dict[str, Any]], original_path: str) -> str:
    os.makedirs(PHASE15_DATASET_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(original_path))[0].replace(" ", "_")[:40] or "backtest"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(PHASE15_DATASET_DIR, f"backtest_learning_{stem}_{stamp}.csv")
    if pd is None:
        import csv
        fields = list(rows[0].keys()) if rows else list(default_ml_row().keys())
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    else:
        pd.DataFrame(rows).to_csv(out, index=False)
    return out


def learn_backtest_csv(path: str, train_after: bool = True, default_timeframe: str = "5m") -> Dict[str, Any]:
    try:
        rows_all = normalize_backtest_csv(path, default_timeframe=default_timeframe)
        rows, skipped_duplicates = filter_new_learning_rows(rows_all, source_hint=f"backtest:{os.path.abspath(path)}")
    except Exception as exc:
        return {"ok": False, "message": f"Backtest import failed: {exc}"}
    csv_path = export_backtest_rows(rows, path)
    imported = {"imported_rows": 0}
    train_result = None
    if rows:
        imported = import_dataset_to_db(csv_path)
        if train_after:
            auto = maybe_auto_retrain(new_rows=len(rows))
            if auto.get("ok"):
                train_result = auto
            else:
                train_result = train_dataset_model(path=None, use_imported=True)
    update_status(last_backtest_import={
        "source_file": path,
        "csv_path": csv_path,
        "rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "imported_rows": imported.get("imported_rows", 0),
        "trained": bool(train_result and train_result.get("ok")),
        "trained_message": (train_result or {}).get("message") if train_result else "training skipped",
        "at": datetime.utcnow().isoformat(),
    })
    return {
        "ok": True,
        "message": f"Backtest learning finished: built {len(rows_all)} labeled rows, skipped {skipped_duplicates} duplicates, saved {csv_path}, imported {imported.get('imported_rows', 0)} new rows.",
        "rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "csv_path": csv_path,
        "imported_rows": imported.get("imported_rows", 0),
        "train_result": train_result,
    }


def create_backtest_template() -> Dict[str, Any]:
    os.makedirs(PHASE15_REPORTS_DIR, exist_ok=True)
    path = os.path.join(PHASE15_REPORTS_DIR, "blue_backtest_import_template.csv")
    rows = [
        {
            "symbol": "XAUUSD", "timeframe": "5m", "action": "BUY", "entry_time": "2026-06-01 09:15:00",
            "entry_price": 2340.50, "sl": 2335.00, "tp1": 2348.75, "tp2": 2354.25,
            "exit_time": "2026-06-01 10:20:00", "exit_price": 2354.25, "profit": 120.0, "pnl_r": 2.5,
            "setup_type": "liquidity_sweep_fvg", "session": "london", "market_regime": "bullish", "news_risk": "low",
            "candlestick_pattern": "bullish_engulfing", "candlestick_bias": "bullish", "candlestick_strength": 4,
        },
        {
            "symbol": "EURUSD", "timeframe": "5m", "action": "SELL", "entry_time": "2026-06-02 13:30:00",
            "entry_price": 1.0850, "sl": 1.0870, "tp1": 1.0820, "tp2": 1.0800,
            "exit_time": "2026-06-02 14:05:00", "exit_price": 1.0870, "profit": -50.0, "pnl_r": -1.0,
            "setup_type": "breakout_retest", "session": "london_new_york_overlap", "market_regime": "sideways", "news_risk": "high",
            "candlestick_pattern": "doji", "candlestick_bias": "neutral", "candlestick_strength": 2,
        },
    ]
    if pd is None:
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
    else:
        pd.DataFrame(rows).to_csv(path, index=False)
    return {"ok": True, "template_file": path}


def backtest_import_help() -> str:
    return (
        "Phase 15 Backtest Learning Commands\n"
        "backtest template                 Create reports/blue_backtest_import_template.csv\n"
        "backtest learn reports/file.csv   Convert a backtest CSV to ML rows, import, and train\n"
        "backtest import reports/file.csv  Same as learn; kept for natural wording\n\n"
        "Accepted columns include many aliases: symbol/pair, action/side/type, entry_time/open_time, entry_price/entry, sl/stop_loss, tp/take_profit, exit_price/close_price, profit/pnl, pnl_r/r_multiple, setup_type/strategy, session, market_regime, news_risk, candle pattern columns."
    )
