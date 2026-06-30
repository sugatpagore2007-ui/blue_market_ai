"""Phase 11 Dataset Learning Brain for Blue Forex Market AI.

This module lets Blue learn from user-supplied CSV datasets, not only from the
built-in journal. It is safe-by-default: it can reduce/block low-probability
signals, but it never forces a trade by itself.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    from config import DATABASE_FILE
except Exception:  # pragma: no cover
    DATABASE_FILE = "blue_market_ai.db"

DATASET_DIR = "datasets"
MODEL_DIR = "models"
DATASET_TABLE = "ml_user_dataset"
DATASET_MODEL_FILE = os.path.join(MODEL_DIR, "blue_dataset_learning_model.joblib")
DATASET_MODEL_META_FILE = os.path.join(MODEL_DIR, "blue_dataset_learning_meta.json")
DATASET_TEMPLATE_FILE = os.path.join(DATASET_DIR, "blue_ml_dataset_template.csv")
DATASET_SAMPLE_FILE = os.path.join(DATASET_DIR, "blue_ml_sample_dataset.csv")

MIN_ROWS_TO_TRAIN = 20
LOW_PROB_BLOCK_THRESHOLD = 45.0
CONFIDENCE_BLEND_WEIGHT = 0.35  # how much trained dataset probability influences final confidence

NUMERIC_FEATURES = [
    "rule_confidence",
    "tf_alignment",
    "spread_pips",
    "atr",
    "rr_ratio",
    "liquidity_sweep",
    "fvg_present",
    "order_block_present",
    "smt_divergence",
    "correlation_risk",
    "entry_stop_distance",
    "target2_rr",
    "candlestick_strength",
    "candlestick_pattern_count",
    "talib_patterns_detected",
]

CATEGORICAL_FEATURES = [
    "symbol_norm",
    "action",
    "setup_type",
    "trade_style",
    "session",
    "market_regime",
    "trend_bias",
    "news_risk",
    "candlestick_bias",
    "candlestick_pattern",
    "talib_available",
]

TEMPLATE_COLUMNS = [
    "timestamp",
    "symbol",
    "timeframe",
    "action",
    "setup_type",
    "trade_style",
    "session",
    "market_regime",
    "trend_bias",
    "news_risk",
    "spread_pips",
    "atr",
    "rr_ratio",
    "rule_confidence",
    "tf_alignment",
    "liquidity_sweep",
    "fvg_present",
    "order_block_present",
    "smt_divergence",
    "correlation_risk",
    "entry",
    "stop_loss",
    "target_1",
    "target_2",
    "candlestick_bias",
    "candlestick_pattern",
    "candlestick_strength",
    "candlestick_pattern_count",
    "talib_available",
    "talib_patterns_detected",
    "source_knowledge",
    "result",
    "pnl_r",
    "notes",
]


def _ensure_dirs() -> None:
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _safe_int_bool(v: Any) -> int:
    text = str(v).strip().lower()
    if text in {"1", "true", "yes", "y", "present", "found", "sweep", "high"}:
        return 1
    try:
        return 1 if float(v) > 0 else 0
    except Exception:
        return 0


def _norm_symbol(v: Any) -> str:
    s = str(v or "").upper().replace("/", "").replace("-", "").replace("_", "").strip()
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
    if "JPY" in s:
        return "USDJPY"
    if "OIL" in s or "WTI" in s:
        return "USOIL"
    if "NAS" in s or "NQ" in s:
        return "NAS100"
    return s[:14] or "UNKNOWN"


def _label_from_result(result: Any, pnl_r: Any = None) -> int | None:
    text = str(result or "").strip().lower()
    pnl = _safe_float(pnl_r, None) if pnl_r is not None and str(pnl_r).strip() != "" else None
    if pnl is not None:
        if pnl > 0:
            return 1
        if pnl < 0:
            return 0
    if text in {"1", "win", "won", "profit", "tp", "target", "target hit", "green"}:
        return 1
    if text in {"0", "loss", "lost", "sl", "stop", "stop loss", "red"}:
        return 0
    if any(w in text for w in ["win", "profit", "tp"]):
        return 1
    if any(w in text for w in ["loss", "lost", "sl", "stop"]):
        return 0
    return None


def _entry_stop_distance(row: Dict[str, Any]) -> float:
    entry = _safe_float(row.get("entry"), 0)
    stop = _safe_float(row.get("stop_loss"), 0)
    if entry and stop:
        return abs(entry - stop)
    return 0.0


def _target2_rr(row: Dict[str, Any]) -> float:
    rr = _safe_float(row.get("rr_ratio"), 0)
    if rr:
        return rr
    entry = _safe_float(row.get("entry"), 0)
    stop = _safe_float(row.get("stop_loss"), 0)
    target = _safe_float(row.get("target_2"), 0)
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk > 0 and reward > 0:
        return reward / risk
    return 0.0


def _normalize_dataframe(df: "pd.DataFrame") -> "pd.DataFrame":
    # Normalize column names.
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {
        "pair": "symbol",
        "instrument": "symbol",
        "side": "action",
        "bias": "trend_bias",
        "confidence": "rule_confidence",
        "win_loss": "result",
        "outcome": "result",
        "profit_r": "pnl_r",
        "r_result": "pnl_r",
        "atr_pips": "atr",
        "entry_price": "entry",
        "sl": "stop_loss",
        "tp1": "target_1",
        "tp2": "target_2",
        "take_profit_1": "target_1",
        "take_profit_2": "target_2",
        "tp": "target_2",
    }
    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]
    for col in TEMPLATE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    records: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        row = {c: r.get(c, "") for c in df.columns}
        label = _label_from_result(row.get("result"), row.get("pnl_r"))
        if label is None:
            # Skip open/unlabeled rows for training, but importing can still store them.
            continue
        symbol = _norm_symbol(row.get("symbol"))
        action = str(row.get("action") or "WAIT").upper().strip()
        if action not in {"BUY", "SELL", "WAIT"}:
            if "buy" in action.lower():
                action = "BUY"
            elif "sell" in action.lower():
                action = "SELL"
            else:
                action = "WAIT"
        clean: Dict[str, Any] = {
            "timestamp": str(row.get("timestamp") or "").strip(),
            "symbol": str(row.get("symbol") or symbol).strip(),
            "symbol_norm": symbol,
            "timeframe": str(row.get("timeframe") or "").strip().lower(),
            "action": action,
            "setup_type": str(row.get("setup_type") or "unknown").strip().lower(),
            "trade_style": str(row.get("trade_style") or "intraday").strip().lower(),
            "session": str(row.get("session") or "unknown").strip().lower(),
            "market_regime": str(row.get("market_regime") or "unknown").strip().lower(),
            "trend_bias": str(row.get("trend_bias") or action.lower()).strip().lower(),
            "news_risk": str(row.get("news_risk") or "normal").strip().lower(),
            "spread_pips": _safe_float(row.get("spread_pips"), 0),
            "atr": _safe_float(row.get("atr"), 0),
            "rr_ratio": _target2_rr(row),
            "rule_confidence": _safe_float(row.get("rule_confidence"), 50),
            "tf_alignment": _safe_float(row.get("tf_alignment"), 0),
            "liquidity_sweep": _safe_int_bool(row.get("liquidity_sweep")),
            "fvg_present": _safe_int_bool(row.get("fvg_present")),
            "order_block_present": _safe_int_bool(row.get("order_block_present")),
            "smt_divergence": _safe_int_bool(row.get("smt_divergence")),
            "correlation_risk": _safe_float(row.get("correlation_risk"), 0),
            "entry": _safe_float(row.get("entry"), 0),
            "stop_loss": _safe_float(row.get("stop_loss"), 0),
            "target_1": _safe_float(row.get("target_1"), 0),
            "target_2": _safe_float(row.get("target_2"), 0),
            "entry_stop_distance": _entry_stop_distance(row),
            "target2_rr": _target2_rr(row),
            "candlestick_bias": str(row.get("candlestick_bias") or "neutral").strip().lower(),
            "candlestick_pattern": str(row.get("candlestick_pattern") or "none").strip().lower().replace(" ", "_"),
            "candlestick_strength": _safe_float(row.get("candlestick_strength"), 0),
            "candlestick_pattern_count": _safe_float(row.get("candlestick_pattern_count"), 1 if str(row.get("candlestick_pattern") or "").strip() else 0),
            "talib_available": str(row.get("talib_available") or "false").strip().lower(),
            "talib_patterns_detected": _safe_float(row.get("talib_patterns_detected"), 0),
            "source_knowledge": str(row.get("source_knowledge") or "").strip().lower(),
            "result": str(row.get("result") or "").strip().lower(),
            "pnl_r": _safe_float(row.get("pnl_r"), 0),
            "label": int(label),
            "notes": str(row.get("notes") or "").strip(),
        }
        records.append(clean)
    return pd.DataFrame(records)


def _make_training_matrix(df: "pd.DataFrame", feature_columns: List[str] | None = None) -> Tuple[Any, List[str]]:
    df = df.copy()
    # Phase 13/14/15 compatibility: older imported rows may not contain the
    # new candlestick/TA-Lib feature columns. Add safe defaults instead of
    # crashing with "not in index".
    for c in NUMERIC_FEATURES:
        if c not in df.columns:
            df[c] = 0
    for c in CATEGORICAL_FEATURES:
        if c not in df.columns:
            df[c] = "unknown"
    base = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    for c in NUMERIC_FEATURES:
        base[c] = base[c].apply(_safe_float).fillna(0)
    for c in CATEGORICAL_FEATURES:
        base[c] = base[c].astype(str).fillna("unknown")
    X = pd.get_dummies(base, columns=CATEGORICAL_FEATURES, dummy_na=False)
    if feature_columns is None:
        feature_columns = list(X.columns)
    for col in feature_columns:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_columns]
    return X, feature_columns


def load_dataset_csv(path: str) -> "pd.DataFrame":
    if pd is None:
        raise RuntimeError("pandas is not installed. Run: pip install pandas")
    if not path:
        raise ValueError("CSV path is required.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    raw = pd.read_csv(path)
    return _normalize_dataframe(raw)


def _connect_db() -> sqlite3.Connection:
    con = sqlite3.connect(DATABASE_FILE)
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {DATASET_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT,
            source_file TEXT,
            payload TEXT,
            label INTEGER
        )
        """
    )
    return con


def import_dataset_to_db(path: str) -> Dict[str, Any]:
    _ensure_dirs()
    df = load_dataset_csv(path)
    con = _connect_db()
    imported = 0
    try:
        for _, r in df.iterrows():
            con.execute(
                f"INSERT INTO {DATASET_TABLE}(imported_at, source_file, payload, label) VALUES(?,?,?,?)",
                (datetime.utcnow().isoformat(), os.path.abspath(path), json.dumps(r.to_dict(), default=str), int(r["label"])),
            )
            imported += 1
        con.commit()
    finally:
        con.close()
    return {"ok": True, "imported_rows": imported, "source_file": path}


def _dataset_from_db(limit: int = 50000) -> "pd.DataFrame":
    if pd is None:
        raise RuntimeError("pandas is not installed. Run: pip install pandas")
    if not os.path.exists(DATABASE_FILE):
        return pd.DataFrame()
    con = _connect_db()
    rows: List[Dict[str, Any]] = []
    try:
        for payload, label in con.execute(f"SELECT payload, label FROM {DATASET_TABLE} ORDER BY id DESC LIMIT ?", (limit,)).fetchall():
            try:
                d = json.loads(payload)
                d["label"] = int(label)
                rows.append(d)
            except Exception:
                continue
    finally:
        con.close()
    return pd.DataFrame(rows)


def train_dataset_model(path: str | None = None, use_imported: bool = True) -> Dict[str, Any]:
    """Train a user-dataset model from CSV or imported rows.

    The saved model predicts probability that a candidate setup becomes a winning
    trade, based on the patterns in the user's supplied rows.
    """
    _ensure_dirs()
    if pd is None:
        return {"ok": False, "message": "pandas is not installed. Run: pip install pandas"}
    frames = []
    source = []
    if path:
        try:
            frames.append(load_dataset_csv(path))
            source.append(path)
        except Exception as e:
            return {"ok": False, "message": f"Could not load CSV: {e}"}
    if use_imported:
        try:
            db_df = _dataset_from_db()
            if not db_df.empty:
                frames.append(db_df)
                source.append("imported_db_rows")
        except Exception:
            pass
    if not frames:
        return {"ok": False, "message": "No dataset found. Use: ml train dataset datasets/blue_ml_sample_dataset.csv"}
    df = pd.concat(frames, ignore_index=True)
    if "label" not in df.columns:
        return {"ok": False, "message": "Dataset has no labels. Add result=win/loss or pnl_r values."}
    df = df.dropna(subset=["label"])
    rows = len(df)
    wins = int((df["label"].astype(int) == 1).sum())
    losses = int((df["label"].astype(int) == 0).sum())
    if rows < MIN_ROWS_TO_TRAIN or wins == 0 or losses == 0:
        return {
            "ok": False,
            "message": f"Need {MIN_ROWS_TO_TRAIN}+ labeled rows with both wins and losses. Found {rows} rows ({wins} wins, {losses} losses).",
            "rows": rows,
            "wins": wins,
            "losses": losses,
        }
    try:
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, roc_auc_score
        import joblib
    except Exception as e:
        return {"ok": False, "message": f"ML packages missing: {e}. Run: pip install scikit-learn joblib"}

    X, feature_columns = _make_training_matrix(df)
    y = df["label"].astype(int)
    # Small datasets can break stratified split; fallback to full fit if needed.
    metrics: Dict[str, Any] = {}
    models: Dict[str, Any] = {}
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        rf = RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=2, random_state=42, class_weight="balanced")
        gb = GradientBoostingClassifier(n_estimators=180, max_depth=3, learning_rate=0.05, random_state=42)
        rf.fit(X_train, y_train)
        gb.fit(X_train, y_train)
        models["random_forest"] = rf
        models["gradient_boosting"] = gb
        preds = ((rf.predict_proba(X_test)[:, 1] + gb.predict_proba(X_test)[:, 1]) / 2 >= 0.5).astype(int)
        prob = (rf.predict_proba(X_test)[:, 1] + gb.predict_proba(X_test)[:, 1]) / 2
        metrics["holdout_accuracy"] = round(float(accuracy_score(y_test, preds)), 3)
        try:
            metrics["holdout_auc"] = round(float(roc_auc_score(y_test, prob)), 3)
        except Exception:
            metrics["holdout_auc"] = "n/a"
    except Exception:
        rf = RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=2, random_state=42, class_weight="balanced")
        rf.fit(X, y)
        models["random_forest"] = rf
        metrics["holdout_accuracy"] = "not enough split data"
        metrics["holdout_auc"] = "not enough split data"

    bundle = {
        "version": "11.0-dataset-learning",
        "trained_at": datetime.utcnow().isoformat(),
        "feature_columns": feature_columns,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "models": models,
        "rows": rows,
        "wins": wins,
        "losses": losses,
        "sources": source,
        "metrics": metrics,
    }
    joblib.dump(bundle, DATASET_MODEL_FILE)
    meta = {k: v for k, v in bundle.items() if k != "models"}
    with open(DATASET_MODEL_META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    return {
        "ok": True,
        "message": f"Dataset ML trained from {rows} rows ({wins} wins, {losses} losses). Models: {', '.join(models.keys())}.",
        "model_file": DATASET_MODEL_FILE,
        "meta_file": DATASET_MODEL_META_FILE,
        "metrics": metrics,
        "rows": rows,
        "wins": wins,
        "losses": losses,
    }


def _load_model_bundle() -> Dict[str, Any] | None:
    try:
        if not os.path.exists(DATASET_MODEL_FILE):
            return None
        import joblib
        return joblib.load(DATASET_MODEL_FILE)
    except Exception:
        return None


def _signal_to_row(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get("action") or "WAIT").upper()
    scores = []
    for d in (signal.get("timeframes") or {}).values():
        try:
            scores.append(float(d.get("score") or 0))
        except Exception:
            pass
    tf_alignment = 0
    for s in scores:
        if action == "BUY" and s > 0:
            tf_alignment += 1
        elif action == "SELL" and s < 0:
            tf_alignment += 1
    entry = _safe_float(signal.get("entry"), 0)
    stop = _safe_float(signal.get("stop_loss"), 0)
    target2 = _safe_float(signal.get("target_2"), 0)
    risk = abs(entry - stop)
    rr = abs(target2 - entry) / risk if risk > 0 and target2 else 0
    news = signal.get("news_filter") or signal.get("macro_brain") or {}
    if isinstance(news, dict):
        news_risk = str(news.get("risk") or news.get("impact") or "normal").lower()
    else:
        news_risk = "normal"
    grades = signal.get("trade_quality_grades") or {}
    regime = str(signal.get("regime") or (signal.get("market_context") or {}).get("regime") or "unknown").lower()
    candle = signal.get("candlestick_brain") or {}
    top_patterns = candle.get("top_patterns") or []
    first_pattern = top_patterns[0] if top_patterns else {}
    candle_pattern = str(first_pattern.get("name") or "none").lower().replace(" ", "_")
    candle_strength = _safe_float(first_pattern.get("strength"), 0)
    candle_pattern_count = len(top_patterns)
    candle_bias = str(candle.get("bias") or "neutral").lower()
    talib_available = str(bool(candle.get("talib_available"))).lower()
    talib_patterns_detected = _safe_float(candle.get("talib_patterns_detected"), 0)
    row = {
        "symbol_norm": _norm_symbol(signal.get("ticker") or signal.get("symbol")),
        "action": action,
        "setup_type": str(grades.get("setup") or grades.get("overall") or "smc_confluence").lower(),
        "trade_style": str(signal.get("trade_style") or "intraday").lower(),
        "session": str(signal.get("session") or "unknown").lower(),
        "market_regime": regime,
        "trend_bias": action.lower(),
        "news_risk": news_risk,
        "rule_confidence": _safe_float(signal.get("confidence"), 50),
        "tf_alignment": float(tf_alignment),
        "spread_pips": _safe_float((signal.get("broker_context") or {}).get("spread_pips"), 0),
        "atr": _safe_float(signal.get("atr"), 0),
        "rr_ratio": rr,
        "liquidity_sweep": 1 if "sweep" in str(signal.get("analyst_reason") or signal.get("human_read") or "").lower() else 0,
        "fvg_present": 1 if "fvg" in str(signal.get("analyst_reason") or signal.get("human_read") or "").lower() else 0,
        "order_block_present": 1 if "order block" in str(signal.get("analyst_reason") or signal.get("human_read") or "").lower() else 0,
        "smt_divergence": 1 if _safe_float((signal.get("smt") or {}).get("score"), 0) != 0 else 0,
        "correlation_risk": _safe_float((signal.get("correlation_engine") or {}).get("same_direction_count"), 0),
        "entry_stop_distance": risk,
        "target2_rr": rr,
        "candlestick_bias": candle_bias,
        "candlestick_pattern": candle_pattern,
        "candlestick_strength": candle_strength,
        "candlestick_pattern_count": candle_pattern_count,
        "talib_available": talib_available,
        "talib_patterns_detected": talib_patterns_detected,
    }
    return row


def predict_signal_probability(signal: Dict[str, Any]) -> Dict[str, Any]:
    if pd is None:
        return {"available": False, "reason": "pandas is not installed."}
    bundle = _load_model_bundle()
    if not bundle:
        return {"available": False, "reason": "No dataset ML model trained yet."}
    models = bundle.get("models") or {}
    if not models:
        return {"available": False, "reason": "Dataset ML model file has no models."}
    row = pd.DataFrame([_signal_to_row(signal)])
    X, _ = _make_training_matrix(row, feature_columns=bundle.get("feature_columns") or [])
    predictions: Dict[str, float] = {}
    errors: Dict[str, str] = {}
    for name, model in models.items():
        try:
            p = float(model.predict_proba(X)[0][1]) * 100
            predictions[name] = round(max(0, min(100, p)), 1)
        except Exception as e:
            errors[name] = str(e)[:180]
    if not predictions:
        return {"available": False, "reason": "Prediction failed.", "errors": errors}
    probability = sum(predictions.values()) / len(predictions)
    return {
        "available": True,
        "dataset_probability": round(probability, 1),
        "predictions": predictions,
        "trained_at": bundle.get("trained_at"),
        "training_rows": bundle.get("rows", 0),
        "metrics": bundle.get("metrics") or {},
        "errors": errors,
    }


def apply_dataset_ml_learning(signal: Dict[str, Any]) -> Dict[str, Any]:
    pred = predict_signal_probability(signal)
    old_conf = _safe_float(signal.get("confidence"), 50)
    engine: Dict[str, Any] = {
        "mode": "not_trained",
        "available": False,
        "old_confidence": old_conf,
        "new_confidence": old_conf,
        "decision": "NO_DATASET_MODEL",
        "note": pred.get("reason", "No dataset model trained yet."),
    }
    if pred.get("available"):
        prob = _safe_float(pred.get("dataset_probability"), old_conf)
        blended = round(old_conf * (1 - CONFIDENCE_BLEND_WEIGHT) + prob * CONFIDENCE_BLEND_WEIGHT, 1)
        engine.update({
            "mode": "trained_user_dataset_model",
            "available": True,
            "dataset_probability": prob,
            "old_confidence": old_conf,
            "new_confidence": blended,
            "predictions": pred.get("predictions", {}),
            "trained_at": pred.get("trained_at"),
            "training_rows": pred.get("training_rows", 0),
            "metrics": pred.get("metrics", {}),
            "decision": "ALLOW" if prob >= LOW_PROB_BLOCK_THRESHOLD else "BLOCK_LOW_DATASET_PROBABILITY",
            "note": f"User-dataset ML probability is {prob}%. Confidence blended from {old_conf}% to {blended}%.",
        })
        if str(signal.get("action", "WAIT")).upper() in {"BUY", "SELL"}:
            signal["confidence"] = int(max(0, min(95, round(blended))))
            if prob < LOW_PROB_BLOCK_THRESHOLD:
                old_action = signal.get("action")
                signal["action_before_dataset_ml"] = old_action
                signal["action"] = "WAIT"
                block_note = f" Dataset ML blocked the trade because probability {prob}% is below {LOW_PROB_BLOCK_THRESHOLD}%."
                signal["analyst_reason"] = str(signal.get("analyst_reason") or "") + block_note
                signal["human_read"] = str(signal.get("human_read") or "") + block_note
    signal["dataset_ml_engine"] = engine
    return signal


def dataset_learning_report() -> str:
    _ensure_dirs()
    meta: Dict[str, Any] = {}
    if os.path.exists(DATASET_MODEL_META_FILE):
        try:
            with open(DATASET_MODEL_META_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    imported_rows = 0
    try:
        con = _connect_db()
        imported_rows = int(con.execute(f"SELECT COUNT(*) FROM {DATASET_TABLE}").fetchone()[0])
        con.close()
    except Exception:
        imported_rows = 0
    model_exists = os.path.exists(DATASET_MODEL_FILE)
    return (
        "Phase 11 User Dataset ML Report\n"
        f"Model ready            : {model_exists}\n"
        f"Imported dataset rows   : {imported_rows}\n"
        f"Training rows in model  : {meta.get('rows', 'not trained')}\n"
        f"Wins / Losses           : {meta.get('wins', 'n/a')} / {meta.get('losses', 'n/a')}\n"
        f"Last trained at         : {meta.get('trained_at', 'not trained yet')}\n"
        f"Model file              : {DATASET_MODEL_FILE}\n"
        f"Template file           : {DATASET_TEMPLATE_FILE}\n"
        f"Sample file             : {DATASET_SAMPLE_FILE}\n"
        "Behavior                : dataset ML can reduce/block weak trades, but never forces live entries.\n"
    )


def dataset_learning_help() -> str:
    return (
        "Phase 11 Dataset Learning Commands\n"
        "1) Create/check template: ml dataset template\n"
        "2) Import your CSV:       ml import dataset path/to/file.csv\n"
        "3) Train from CSV:        ml train dataset path/to/file.csv\n"
        "4) Train imported rows:   ml train imported dataset\n"
        "5) Check status:          ml dataset report\n\n"
        "Required label: result=win/loss OR pnl_r positive/negative.\n"
        "Best columns: symbol, action, setup_type, trade_style, session, market_regime, news_risk, spread_pips, atr, rr_ratio, rule_confidence, tf_alignment, liquidity_sweep, fvg_present, order_block_present, smt_divergence, candlestick_bias, candlestick_pattern, candlestick_strength, candlestick_pattern_count, talib_available, talib_patterns_detected, result/pnl_r.\n"
    )


def export_dataset_template() -> Dict[str, Any]:
    _ensure_dirs()
    if pd is None:
        # Basic fallback without pandas.
        with open(DATASET_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(TEMPLATE_COLUMNS) + "\n")
        return {"ok": True, "template_file": DATASET_TEMPLATE_FILE, "sample_file": DATASET_SAMPLE_FILE}
    if not os.path.exists(DATASET_TEMPLATE_FILE):
        pd.DataFrame(columns=TEMPLATE_COLUMNS).to_csv(DATASET_TEMPLATE_FILE, index=False)
    if not os.path.exists(DATASET_SAMPLE_FILE):
        sample_rows = _sample_rows()
        pd.DataFrame(sample_rows, columns=TEMPLATE_COLUMNS).to_csv(DATASET_SAMPLE_FILE, index=False)
    return {"ok": True, "template_file": DATASET_TEMPLATE_FILE, "sample_file": DATASET_SAMPLE_FILE}


def _sample_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    setups = ["liquidity_sweep_fvg", "trend_pullback", "breakout_retest", "reversal_ob"]
    sessions = ["london", "new_york", "asia", "london", "new_york"]
    for i in range(30):
        sym = symbols[i % len(symbols)]
        action = "BUY" if i % 2 == 0 else "SELL"
        win = 1 if i % 5 in {0, 1, 3} else 0
        conf = 72 + (i % 18)
        rr = 1.4 + (i % 4) * 0.35
        spread = 2 + (i % 6)
        rows.append({
            "timestamp": f"2026-06-{1 + (i % 20):02d} 10:{i%60:02d}:00",
            "symbol": sym,
            "timeframe": "5m",
            "action": action,
            "setup_type": setups[i % len(setups)],
            "trade_style": "intraday",
            "session": sessions[i % len(sessions)],
            "market_regime": "trend_expansion" if i % 3 else "range_rotation",
            "trend_bias": "bullish" if action == "BUY" else "bearish",
            "news_risk": "normal" if i % 7 else "high",
            "spread_pips": spread,
            "atr": round(0.001 + (i % 9) * 0.0002, 5),
            "rr_ratio": round(rr, 2),
            "rule_confidence": conf,
            "tf_alignment": 3 + (i % 3),
            "liquidity_sweep": 1 if i % 2 else 0,
            "fvg_present": 1 if i % 3 else 0,
            "order_block_present": 1 if i % 4 else 0,
            "smt_divergence": 1 if i % 6 == 0 else 0,
            "correlation_risk": 0 if i % 4 else 1,
            "entry": 100 + i,
            "stop_loss": 99 + i if action == "BUY" else 101 + i,
            "target_1": 101.5 + i if action == "BUY" else 98.5 + i,
            "target_2": 102.5 + i if action == "BUY" else 97.5 + i,
            "result": "win" if win else "loss",
            "pnl_r": 1.5 if win else -1.0,
            "notes": "sample only - replace with real tested/demo trades",
        })
    return rows
