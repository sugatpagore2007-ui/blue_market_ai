"""Phase 15 Blue journal importer.

Turns Blue's own closed journal/demo trades into Phase 11 ML rows. This is useful
when trades were tracked inside Blue instead of imported from MT5/backtest CSV.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    from config import DATABASE_FILE, PHASE15_DATASET_DIR
except Exception:
    DATABASE_FILE = "blue_market_ai.db"
    PHASE15_DATASET_DIR = "datasets"

from learning.trade_labeler import default_ml_row, norm_symbol, safe_float
from learning.dataset_learning import import_dataset_to_db, train_dataset_model
from learning.auto_history_learning import maybe_auto_retrain, update_status, filter_new_learning_rows


def _read_closed_journal_rows(limit: int = 50000) -> List[Dict[str, Any]]:
    if not os.path.exists(DATABASE_FILE):
        return []
    con = sqlite3.connect(DATABASE_FILE)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM journal WHERE result!='OPEN' ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        con.close()


def _journal_to_ml_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return default_ml_row(
        timestamp=r.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        symbol=norm_symbol(r.get("ticker") or r.get("symbol")),
        timeframe="5m",
        action=r.get("action") or "WAIT",
        setup_type=r.get("setup_type") or "blue_journal_trade",
        session=r.get("session") or "unknown",
        market_regime=r.get("market_regime") or "unknown",
        news_risk=r.get("news_risk") or "unknown",
        spread_pips=safe_float(r.get("spread_at_entry"), 0.0),
        atr=safe_float(r.get("atr_at_entry"), 0.0),
        rr_ratio=safe_float(r.get("rr_ratio") or r.get("rr"), 0.0),
        entry=r.get("entry"),
        stop_loss=r.get("stop_loss"),
        target_1=r.get("target_1"),
        target_2=r.get("target_2"),
        profit=r.get("pnl"),
        pnl_r=r.get("rr"),
        result=r.get("outcome_label") or r.get("result"),
        source="blue_journal",
        source_knowledge="phase15_blue_journal_import",
        notes=f"Phase 15 journal import. Journal id={r.get('id')}; notes={r.get('notes') or ''}",
    )


def learn_blue_journal(train_after: bool = True) -> Dict[str, Any]:
    rows_raw = _read_closed_journal_rows()
    rows_all = [_journal_to_ml_row(r) for r in rows_raw]
    rows_all = [r for r in rows_all if r.get("result") in {"win", "loss"}]
    rows, skipped_duplicates = filter_new_learning_rows(rows_all, source_hint="blue_journal")
    os.makedirs(PHASE15_DATASET_DIR, exist_ok=True)
    path = os.path.join(PHASE15_DATASET_DIR, f"blue_journal_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    if pd is None:
        import csv
        fields = list(rows[0].keys()) if rows else list(default_ml_row().keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
    else:
        pd.DataFrame(rows).to_csv(path, index=False)
    imported = {"imported_rows": 0}
    train_result = None
    if rows:
        imported = import_dataset_to_db(path)
        if train_after:
            auto = maybe_auto_retrain(new_rows=len(rows))
            train_result = auto if auto.get("ok") else train_dataset_model(path=None, use_imported=True)
    update_status(last_journal_import={
        "csv_path": path,
        "closed_journal_rows_read": len(rows_raw),
        "labeled_rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "imported_rows": imported.get("imported_rows", 0),
        "trained": bool(train_result and train_result.get("ok")),
        "trained_message": (train_result or {}).get("message") if train_result else "training skipped",
        "at": datetime.utcnow().isoformat(),
    })
    return {
        "ok": True,
        "message": f"Blue journal learning finished: read {len(rows_raw)} closed journal trades, built {len(rows_all)} labeled rows, skipped {skipped_duplicates} duplicates, saved {path}, imported {imported.get('imported_rows', 0)} new rows.",
        "rows": len(rows),
        "rows_seen": len(rows_all),
        "duplicates_skipped": skipped_duplicates,
        "csv_path": path,
        "imported_rows": imported.get("imported_rows", 0),
        "train_result": train_result,
    }
