"""Phase 15 Auto History Learning status, settings and retraining helpers."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict

try:
    from config import DATABASE_FILE
except Exception:
    DATABASE_FILE = "blue_market_ai.db"

try:
    from config import PHASE15_AUTO_HISTORY_LEARNING_ENABLED, PHASE15_AUTO_RETRAIN_ENABLED, PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS
except Exception:
    PHASE15_AUTO_HISTORY_LEARNING_ENABLED = True
    PHASE15_AUTO_RETRAIN_ENABLED = True
    PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS = 25

SETTINGS_FILE = "phase15_auto_learning_settings.json"
STATUS_FILE = "phase15_auto_learning_status.json"
DATASET_TABLE = "ml_user_dataset"


# Startup auto-learning controls. These defaults make Blue learn whenever the app starts,
# but remain read-only: it imports history/journal/backtest rows and trains ML; it never places trades.
try:
    from config import (
        PHASE15_STARTUP_AUTO_LEARN_ENABLED,
        PHASE15_STARTUP_LEARN_JOURNAL,
        PHASE15_STARTUP_LEARN_MT5,
        PHASE15_STARTUP_LEARN_BACKTEST_REPORTS,
        PHASE15_STARTUP_MT5_HISTORY_DAYS,
        PHASE15_STARTUP_HISTORY_TIMEFRAME,
        PHASE15_STARTUP_BACKTEST_GLOBS,
    )
except Exception:
    PHASE15_STARTUP_AUTO_LEARN_ENABLED = True
    PHASE15_STARTUP_LEARN_JOURNAL = True
    PHASE15_STARTUP_LEARN_MT5 = True
    PHASE15_STARTUP_LEARN_BACKTEST_REPORTS = True
    PHASE15_STARTUP_MT5_HISTORY_DAYS = 30
    PHASE15_STARTUP_HISTORY_TIMEFRAME = "5m"
    PHASE15_STARTUP_BACKTEST_GLOBS = ["reports/*.csv", "reports/auto_learn/*.csv"]

PROCESSED_KEYS_FILE = "phase15_processed_learning_keys.json"


def _default_settings() -> Dict[str, Any]:
    return {
        "auto_learning_enabled": bool(PHASE15_AUTO_HISTORY_LEARNING_ENABLED),
        "auto_retrain_enabled": bool(PHASE15_AUTO_RETRAIN_ENABLED),
        "auto_retrain_after_new_rows": int(PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS),
        "learning_can_block_trades": True,
        "learning_can_place_trades": False,
        "last_updated": datetime.utcnow().isoformat(),
    }


def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(_default_settings())
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = _default_settings()
        base.update(data or {})
        return base
    except Exception:
        return _default_settings()


def save_settings(settings: Dict[str, Any]) -> None:
    settings = dict(settings)
    settings["last_updated"] = datetime.utcnow().isoformat()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def set_auto_learning(enabled: bool) -> str:
    s = load_settings()
    s["auto_learning_enabled"] = bool(enabled)
    save_settings(s)
    return "Phase 15 auto learning is ON." if enabled else "Phase 15 auto learning is OFF. Manual import/train commands still work."


def set_auto_retrain(enabled: bool) -> str:
    s = load_settings()
    s["auto_retrain_enabled"] = bool(enabled)
    save_settings(s)
    return "Phase 15 auto retrain is ON." if enabled else "Phase 15 auto retrain is OFF. Use retrain now manually."


def _db_count() -> int:
    if not os.path.exists(DATABASE_FILE):
        return 0
    try:
        con = sqlite3.connect(DATABASE_FILE)
        con.execute(f"CREATE TABLE IF NOT EXISTS {DATASET_TABLE} (id INTEGER PRIMARY KEY AUTOINCREMENT, imported_at TEXT, source_file TEXT, payload TEXT, label INTEGER)")
        n = int(con.execute(f"SELECT COUNT(*) FROM {DATASET_TABLE}").fetchone()[0])
        con.close()
        return n
    except Exception:
        return 0


def _load_status() -> Dict[str, Any]:
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def update_status(**kwargs: Any) -> None:
    data = _load_status()
    data.update(kwargs)
    data["updated_at"] = datetime.utcnow().isoformat()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def retrain_now() -> Dict[str, Any]:
    try:
        from learning.dataset_learning import train_dataset_model
        return train_dataset_model(path=None, use_imported=True)
    except Exception as exc:
        return {"ok": False, "message": f"Retrain failed: {exc}"}


def maybe_auto_retrain(new_rows: int = 0) -> Dict[str, Any]:
    s = load_settings()
    if not s.get("auto_retrain_enabled", True):
        return {"ok": False, "message": "Auto retrain is OFF. Use: retrain now"}
    threshold = int(s.get("auto_retrain_after_new_rows") or 25)
    if int(new_rows or 0) < threshold:
        return {"ok": False, "message": f"Imported {new_rows} new rows. Auto retrain waits for {threshold}+ new rows."}
    res = retrain_now()
    update_status(last_auto_retrain=res, last_auto_retrain_new_rows=new_rows)
    return res


def _summarize_last(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "none")
    bits = []
    if "imported_rows" in value:
        bits.append(f"imported={value.get('imported_rows')}")
    if "new_rows" in value:
        bits.append(f"new_rows={value.get('new_rows')}")
    if "rows" in value:
        bits.append(f"rows={value.get('rows')}")
    if "duplicates_skipped" in value:
        bits.append(f"duplicates_skipped={value.get('duplicates_skipped')}")
    if "trained" in value:
        bits.append(f"trained={value.get('trained')}")
    if "at" in value:
        bits.append(f"at={str(value.get('at'))[:19]}")
    return ", ".join(bits) if bits else str(value)


def phase15_status_text() -> str:
    s = load_settings()
    st = _load_status()
    imported_rows = _db_count()
    return (
        "Phase 15.1 Startup Auto Learning: ACTIVE\n"
        f"Auto learning enabled       : {s.get('auto_learning_enabled')}\n"
        f"Auto retrain enabled        : {s.get('auto_retrain_enabled')}\n"
        f"Retrain after new rows      : {s.get('auto_retrain_after_new_rows')}\n"
        f"Imported ML dataset rows    : {imported_rows}\n"
        f"Last startup auto-learning  : {_summarize_last(st.get('last_startup_auto_learning'))}\n"
        f"Last MT5 import             : {_summarize_last(st.get('last_mt5_import'))}\n"
        f"Last backtest import        : {_summarize_last(st.get('last_backtest_import'))}\n"
        f"Last journal import         : {_summarize_last(st.get('last_journal_import'))}\n"
        f"Last background learning    : {_summarize_last(st.get('last_background_auto_learning'))}\n"
        "Live trading by ML alone    : disabled\n"
        "Commands: background learn status | background learn now | startup learn now | mt5 learn history 30d | backtest learn reports/file.csv | auto learn on/off | retrain now | learning report"
    )


def learning_report_text() -> str:
    from learning.dataset_learning import dataset_learning_report
    base = phase15_status_text()
    return base + "\n\n" + dataset_learning_report()


def _row_key(row: Dict[str, Any], source_hint: str = "") -> str:
    """Stable key so startup learning imports only new closed trades/backtest rows."""
    import hashlib
    parts = [
        source_hint or str(row.get("source") or row.get("source_knowledge") or "unknown"),
        str(row.get("timestamp") or "").strip(),
        str(row.get("symbol") or row.get("symbol_norm") or "").upper().strip(),
        str(row.get("timeframe") or "").lower().strip(),
        str(row.get("action") or "").upper().strip(),
        str(row.get("entry") or "").strip(),
        str(row.get("stop_loss") or "").strip(),
        str(row.get("target_1") or "").strip(),
        str(row.get("target_2") or "").strip(),
        str(row.get("pnl_r") or "").strip(),
        str(row.get("result") or "").lower().strip(),
        str(row.get("notes") or "")[:300],
    ]
    raw = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _load_processed_keys() -> Dict[str, Any]:
    if not os.path.exists(PROCESSED_KEYS_FILE):
        return {"keys": [], "updated_at": None}
    try:
        with open(PROCESSED_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if isinstance(data.get("keys"), list):
            return data
        return {"keys": [], "updated_at": None}
    except Exception:
        return {"keys": [], "updated_at": None}


def _save_processed_keys(keys: set[str]) -> None:
    # Keep the file bounded so long-running users do not grow it forever.
    trimmed = list(keys)[-50000:]
    with open(PROCESSED_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump({"keys": trimmed, "updated_at": datetime.utcnow().isoformat()}, f, indent=2)


def filter_new_learning_rows(rows: list[Dict[str, Any]], source_hint: str = "") -> tuple[list[Dict[str, Any]], int]:
    """Return rows not seen before and mark them as processed immediately.

    Used by startup/manual history importers to stop duplicate ML rows each time
    Blue starts.
    """
    state = _load_processed_keys()
    keys = set(state.get("keys") or [])
    new_rows: list[Dict[str, Any]] = []
    skipped = 0
    for row in rows or []:
        k = _row_key(row, source_hint=source_hint)
        if k in keys:
            skipped += 1
            continue
        keys.add(k)
        new_rows.append(row)
    _save_processed_keys(keys)
    return new_rows, skipped


def run_startup_auto_learning(verbose: bool = False) -> Dict[str, Any]:
    """Run once when main.py starts: journal + MT5 + backtest learning.

    This is intentionally read-only. If MT5 is not installed/running/logged in,
    the MT5 step is skipped and Blue still starts normally.
    """
    import glob

    settings = load_settings()
    if not bool(settings.get("auto_learning_enabled", True)) or not bool(PHASE15_STARTUP_AUTO_LEARN_ENABLED):
        return {
            "ok": True,
            "ran": False,
            "message": "Startup auto-learning skipped because auto learning is OFF.",
            "new_rows": 0,
            "trained": False,
        }

    total_new = 0
    steps: list[str] = []
    errors: list[str] = []

    # 1) Learn from Blue's own journal/demo trades.
    if bool(PHASE15_STARTUP_LEARN_JOURNAL):
        try:
            from learning.journal_history_importer import learn_blue_journal
            res = learn_blue_journal(train_after=False)
            n = int(res.get("imported_rows") or 0)
            total_new += n
            steps.append(f"journal:{n}")
        except Exception as exc:
            errors.append(f"journal skipped: {exc}")

    # 2) Learn from MT5 closed history if the terminal is available.
    if bool(PHASE15_STARTUP_LEARN_MT5):
        try:
            from learning.mt5_history_importer import learn_mt5_history
            res = learn_mt5_history(
                days=int(PHASE15_STARTUP_MT5_HISTORY_DAYS),
                timeframe=str(PHASE15_STARTUP_HISTORY_TIMEFRAME),
                train_after=False,
                reconstruct=True,
            )
            if res.get("ok"):
                n = int(res.get("imported_rows") or 0)
                total_new += n
                steps.append(f"mt5:{n}")
            else:
                errors.append(f"mt5 skipped: {res.get('message')}")
        except Exception as exc:
            errors.append(f"mt5 skipped: {exc}")

    # 3) Learn from backtest CSV files placed in reports/. Template/sample files are ignored.
    if bool(PHASE15_STARTUP_LEARN_BACKTEST_REPORTS):
        seen_files: set[str] = set()
        for pattern in PHASE15_STARTUP_BACKTEST_GLOBS:
            for path in glob.glob(pattern):
                base = os.path.basename(path).lower()
                if path in seen_files or any(x in base for x in ["template", "sample", "example"]):
                    continue
                seen_files.add(path)
                try:
                    from learning.backtest_importer import learn_backtest_csv
                    res = learn_backtest_csv(path, train_after=False)
                    if res.get("ok"):
                        n = int(res.get("imported_rows") or 0)
                        total_new += n
                        steps.append(f"backtest:{os.path.basename(path)}:{n}")
                    else:
                        errors.append(f"backtest skipped {os.path.basename(path)}: {res.get('message')}")
                except Exception as exc:
                    errors.append(f"backtest skipped {os.path.basename(path)}: {exc}")

    train_result = None
    trained = False
    if total_new > 0 and bool(settings.get("auto_retrain_enabled", True)):
        train_result = maybe_auto_retrain(new_rows=total_new)
        trained = bool(train_result and train_result.get("ok"))

    update_status(last_startup_auto_learning={
        "new_rows": total_new,
        "steps": steps,
        "errors": errors[:10],
        "trained": trained,
        "train_message": (train_result or {}).get("message") if train_result else "no new rows / retrain not needed",
        "at": datetime.utcnow().isoformat(),
    })

    msg = f"Startup auto-learning checked sources; imported {total_new} new ML rows."
    if train_result:
        msg += " " + str(train_result.get("message", ""))
    if errors and verbose:
        msg += " Skips: " + "; ".join(errors[:3])
    return {"ok": True, "ran": True, "message": msg, "new_rows": total_new, "steps": steps, "errors": errors, "trained": trained, "train_result": train_result}
