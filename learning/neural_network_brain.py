"""Phase 15.19 Neural Network Brain for Blue Forex Market AI.

Best model path:
- TensorFlow/Keras CNN + BiLSTM + Attention when TensorFlow is installed.
- sklearn MLP fallback when TensorFlow is not available.

Safety design:
- Advisory and confirmation-only.
- Can reduce confidence or block weak learned-history setups.
- Never opens, modifies, or closes MT5 orders by itself.
- Missing packages/model/data never crash Blue; the module stays neutral.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import joblib
except Exception:  # pragma: no cover
    joblib = None  # type: ignore

try:
    from config import (
        PHASE15_19_NEURAL_NETWORK_ENABLED,
        PHASE15_19_NEURAL_NETWORK_BACKGROUND_ENABLED,
        PHASE15_19_NEURAL_MIN_HOURS_BETWEEN_TRAINING,
        PHASE15_19_NEURAL_CONFIDENCE_BLEND_WEIGHT,
        PHASE15_19_NEURAL_LOW_PROB_BLOCK_THRESHOLD,
        PHASE15_19_NEURAL_MIN_ROWS_TO_TRAIN,
        PHASE15_19_NEURAL_MODEL_DIR,
        PHASE15_19_NEURAL_KERAS_MODEL_FILE,
        PHASE15_19_NEURAL_FALLBACK_MODEL_FILE,
        PHASE15_19_NEURAL_META_FILE,
        PHASE15_19_NEURAL_STATE_FILE,
        PHASE15_19_NEURAL_USE_TENSORFLOW_IF_AVAILABLE,
        PHASE15_19_NEURAL_SEQUENCE_LENGTH,
        PHASE15_19_NEURAL_EPOCHS,
        PHASE15_19_NEURAL_BATCH_SIZE,
        PHASE15_19_NEURAL_PATIENCE,
    )
except Exception:  # pragma: no cover
    PHASE15_19_NEURAL_NETWORK_ENABLED = True
    PHASE15_19_NEURAL_NETWORK_BACKGROUND_ENABLED = True
    PHASE15_19_NEURAL_MIN_HOURS_BETWEEN_TRAINING = 12
    PHASE15_19_NEURAL_CONFIDENCE_BLEND_WEIGHT = 0.30
    PHASE15_19_NEURAL_LOW_PROB_BLOCK_THRESHOLD = 42.0
    PHASE15_19_NEURAL_MIN_ROWS_TO_TRAIN = 40
    PHASE15_19_NEURAL_MODEL_DIR = "models"
    PHASE15_19_NEURAL_KERAS_MODEL_FILE = os.path.join("models", "blue_cnn_bilstm_attention.keras")
    PHASE15_19_NEURAL_FALLBACK_MODEL_FILE = os.path.join("models", "blue_neural_mlp_fallback.joblib")
    PHASE15_19_NEURAL_META_FILE = os.path.join("models", "blue_neural_network_brain_meta.json")
    PHASE15_19_NEURAL_STATE_FILE = "phase15_19_neural_network_state.json"
    PHASE15_19_NEURAL_USE_TENSORFLOW_IF_AVAILABLE = True
    PHASE15_19_NEURAL_SEQUENCE_LENGTH = 24
    PHASE15_19_NEURAL_EPOCHS = 35
    PHASE15_19_NEURAL_BATCH_SIZE = 32
    PHASE15_19_NEURAL_PATIENCE = 6

try:
    from learning.dataset_learning import (
        load_dataset_csv,
        _dataset_from_db,
        _make_training_matrix,
        _signal_to_row,
        _safe_float,
        MIN_ROWS_TO_TRAIN,
    )
except Exception:  # pragma: no cover
    load_dataset_csv = None  # type: ignore
    _dataset_from_db = None  # type: ignore
    _make_training_matrix = None  # type: ignore
    _signal_to_row = None  # type: ignore
    MIN_ROWS_TO_TRAIN = 20
    def _safe_float(v: Any, default: float = 0.0) -> float:  # type: ignore
        try:
            return float(v)
        except Exception:
            return float(default)

PHASE15_19_VERSION = "15.19-cnn-bilstm-attention-neural-brain"
DEFAULT_MIN_ROWS = max(int(PHASE15_19_NEURAL_MIN_ROWS_TO_TRAIN or 40), int(MIN_ROWS_TO_TRAIN or 20))


def _utc_now() -> datetime:
    return datetime.utcnow()


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utc_now()).isoformat()


def _ensure_dirs() -> None:
    os.makedirs(str(PHASE15_19_NEURAL_MODEL_DIR or "models"), exist_ok=True)


def _read_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if data is not None else default
    except Exception:
        pass
    return default


def _write_json(path: str, data: Any) -> None:
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def _state() -> Dict[str, Any]:
    data = _read_json(PHASE15_19_NEURAL_STATE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("enabled", bool(PHASE15_19_NEURAL_NETWORK_ENABLED))
    data.setdefault("background_enabled", bool(PHASE15_19_NEURAL_NETWORK_BACKGROUND_ENABLED))
    data.setdefault("last_training_at", None)
    data.setdefault("last_message", "Neural Network Brain has not trained yet.")
    return data


def _save_state(**updates: Any) -> Dict[str, Any]:
    data = _state()
    data.update(updates)
    data["updated_at"] = _iso()
    _write_json(PHASE15_19_NEURAL_STATE_FILE, data)
    return data


def _tensorflow_available() -> Tuple[bool, str, Any]:
    if not bool(PHASE15_19_NEURAL_USE_TENSORFLOW_IF_AVAILABLE):
        return False, "TensorFlow disabled in config", None
    try:
        import tensorflow as tf  # type: ignore
        return True, "TensorFlow/Keras available", tf
    except Exception as exc:
        return False, str(exc), None


def neural_help() -> str:
    return (
        "Phase 15.19 Neural Network Brain\n"
        "Best model: CNN + BiLSTM + Attention for pattern confirmation.\n"
        "Fallback: sklearn MLP if TensorFlow is not installed.\n\n"
        "Commands:\n"
        "  neural help / nn help              -> show this help\n"
        "  neural train / nn train            -> train from imported trade dataset rows\n"
        "  neural train dataset <csv>         -> train from a CSV plus imported rows\n"
        "  neural report / nn status          -> show model/training status\n"
        "  neural predict gold / nn gold      -> analyze symbol with NN confirmation\n"
        "  neural on / neural off             -> enable/disable NN scoring\n"
        "  neural background on/off           -> enable/disable background retraining\n\n"
        "Safety: the neural brain can confirm, reduce confidence, or block weak setups. It never punches orders by itself."
    )


def set_neural_network(enabled: Optional[bool] = None, background: Optional[bool] = None) -> str:
    updates: Dict[str, Any] = {}
    if enabled is not None:
        updates["enabled"] = bool(enabled)
    if background is not None:
        updates["background_enabled"] = bool(background)
    st = _save_state(**updates)
    return (
        "Neural Network Brain settings updated.\n"
        f"Enabled             : {st.get('enabled')}\n"
        f"Background retrain  : {st.get('background_enabled')}"
    )


def _load_training_frames(path: Optional[str] = None, use_imported: bool = True) -> tuple[Any, List[str]]:
    if pd is None:
        raise RuntimeError("pandas is not installed. Run: pip install pandas")
    if load_dataset_csv is None or _dataset_from_db is None:
        raise RuntimeError("dataset learning helpers are unavailable")
    frames = []
    sources: List[str] = []
    if path:
        frames.append(load_dataset_csv(path))
        sources.append(path)
    if use_imported:
        try:
            db_df = _dataset_from_db()
            if db_df is not None and not db_df.empty:
                frames.append(db_df)
                sources.append("imported_db_rows")
        except Exception:
            pass
    if not frames:
        return pd.DataFrame(), sources
    df = pd.concat(frames, ignore_index=True)
    if "label" not in df.columns:
        return pd.DataFrame(), sources
    df = df.dropna(subset=["label"]).copy()
    df["label"] = df["label"].astype(int)
    return df, sources


def _matrix_to_sequence(X: Any, seq_len: int) -> Any:
    """Convert tabular setup features into a tiny sequence for CNN/BiLSTM.

    Blue's available labeled history is mostly setup/trade rows, not raw candle tensors.
    This reshape lets the CNN+BiLSTM+Attention model learn feature-sequence interactions
    immediately, while still allowing a future upgrade to feed true candle windows.
    """
    if np is None:
        raise RuntimeError("numpy is not installed. Run: pip install numpy")
    arr = X.to_numpy(dtype="float32") if hasattr(X, "to_numpy") else np.asarray(X, dtype="float32")
    seq_len = max(4, int(seq_len or 24))
    n_rows, n_features = arr.shape
    pad = (-n_features) % seq_len
    if pad:
        arr = np.pad(arr, ((0, 0), (0, pad)), mode="constant")
    channels = arr.shape[1] // seq_len
    return arr.reshape(n_rows, seq_len, channels).astype("float32")


def _build_attention_model(tf: Any, input_shape: tuple[int, int]) -> Any:
    layers = tf.keras.layers
    inputs = layers.Input(shape=input_shape, name="setup_feature_sequence")
    x = layers.Conv1D(filters=32, kernel_size=3, padding="same", activation="relu", name="cnn_candle_pattern_filter")(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.15)(x)
    x = layers.Bidirectional(layers.LSTM(48, return_sequences=True), name="bilstm_market_sequence_memory")(x)
    # Attention: learn which feature/candle-style steps matter most.
    score = layers.Dense(1, activation="tanh", name="attention_score")(x)
    weights = layers.Softmax(axis=1, name="attention_weights")(score)
    context = layers.Multiply(name="attention_apply")([x, weights])
    context = layers.Lambda(lambda t: tf.reduce_sum(t, axis=1), name="attention_context")(context)
    x = layers.Dense(48, activation="relu")(context)
    x = layers.Dropout(0.20)(x)
    outputs = layers.Dense(1, activation="sigmoid", name="win_probability")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="Blue_CNN_BiLSTM_Attention")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="binary_crossentropy", metrics=["accuracy", tf.keras.metrics.AUC(name="auc")])
    return model


def _train_keras_attention(X: Any, y: Any, feature_columns: List[str], rows: int, wins: int, losses: int, sources: List[str]) -> Dict[str, Any]:
    if np is None:
        raise RuntimeError("numpy is missing")
    ok_tf, tf_msg, tf = _tensorflow_available()
    if not ok_tf or tf is None:
        raise RuntimeError("TensorFlow unavailable: " + tf_msg)
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, roc_auc_score

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    seq_len = int(PHASE15_19_NEURAL_SEQUENCE_LENGTH or 24)
    X_seq = _matrix_to_sequence(pd.DataFrame(X_scaled, columns=feature_columns), seq_len)
    y_arr = np.asarray(y, dtype="float32")

    metrics: Dict[str, Any] = {}
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_seq, y_arr, test_size=0.25, random_state=42, stratify=y_arr)
        validation_data = (X_test, y_test)
    except Exception as split_exc:
        X_train, y_train = X_seq, y_arr
        X_test, y_test = None, None
        validation_data = None
        metrics["training_note"] = "holdout split skipped: " + str(split_exc)[:160]

    model = _build_attention_model(tf, input_shape=(X_seq.shape[1], X_seq.shape[2]))
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss" if validation_data else "loss", patience=int(PHASE15_19_NEURAL_PATIENCE or 6), restore_best_weights=True)
    ]
    model.fit(
        X_train,
        y_train,
        validation_data=validation_data,
        epochs=int(PHASE15_19_NEURAL_EPOCHS or 35),
        batch_size=int(PHASE15_19_NEURAL_BATCH_SIZE or 32),
        verbose=0,
        callbacks=callbacks,
    )

    if X_test is not None:
        prob = model.predict(X_test, verbose=0).reshape(-1)
        preds = (prob >= 0.5).astype(int)
        metrics["holdout_accuracy"] = round(float(accuracy_score(y_test, preds)), 3)
        try:
            metrics["holdout_auc"] = round(float(roc_auc_score(y_test, prob)), 3)
        except Exception:
            metrics["holdout_auc"] = "n/a"
    else:
        metrics.setdefault("holdout_accuracy", "not enough split data")
        metrics.setdefault("holdout_auc", "not enough split data")

    _ensure_dirs()
    model.save(PHASE15_19_NEURAL_KERAS_MODEL_FILE)
    scaler_bundle = {
        "version": PHASE15_19_VERSION,
        "trained_at": _iso(),
        "model_type": "CNN + BiLSTM + Attention (TensorFlow/Keras)",
        "feature_columns": feature_columns,
        "sequence_length": X_seq.shape[1],
        "channels": X_seq.shape[2],
        "scaler": scaler,
        "rows": rows,
        "wins": wins,
        "losses": losses,
        "sources": sources,
        "metrics": metrics,
    }
    # Store scaler/feature metadata in joblib fallback path with .joblib filename? Use meta sidecar.
    scaler_file = os.path.join(str(PHASE15_19_NEURAL_MODEL_DIR or "models"), "blue_cnn_bilstm_attention_scaler.joblib")
    if joblib is not None:
        joblib.dump(scaler_bundle, scaler_file)
    meta = {k: v for k, v in scaler_bundle.items() if k != "scaler"}
    meta["keras_model_file"] = PHASE15_19_NEURAL_KERAS_MODEL_FILE
    meta["scaler_file"] = scaler_file
    meta["safety"] = "Advisory only. Neural brain can reduce/block; it never forces MT5 order execution."
    _write_json(PHASE15_19_NEURAL_META_FILE, meta)
    return {"ok": True, "trained": True, "message": f"CNN + BiLSTM + Attention Neural Brain trained from {rows} rows ({wins} wins, {losses} losses).", "meta": meta}


def _train_mlp_fallback(X: Any, y: Any, feature_columns: List[str], rows: int, wins: int, losses: int, sources: List[str], reason: str) -> Dict[str, Any]:
    if joblib is None:
        return {"ok": False, "trained": False, "message": "joblib is missing. Run: pip install joblib"}
    try:
        from sklearn.metrics import accuracy_score, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as e:
        return {"ok": False, "trained": False, "message": f"Neural packages missing: {e}. Run: pip install scikit-learn joblib"}

    neural = Pipeline([
        ("scaler", StandardScaler()),
        ("mlp", MLPClassifier(
            hidden_layer_sizes=(96, 48, 24),
            activation="relu",
            solver="adam",
            alpha=0.0008,
            learning_rate_init=0.001,
            max_iter=700,
            early_stopping=True,
            validation_fraction=0.2,
            random_state=42,
        )),
    ])
    metrics: Dict[str, Any] = {"fallback_reason": reason[:240]}
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        neural.fit(X_train, y_train)
        prob = neural.predict_proba(X_test)[:, 1]
        preds = (prob >= 0.5).astype(int)
        metrics["holdout_accuracy"] = round(float(accuracy_score(y_test, preds)), 3)
        try:
            metrics["holdout_auc"] = round(float(roc_auc_score(y_test, prob)), 3)
        except Exception:
            metrics["holdout_auc"] = "n/a"
    except Exception as split_exc:
        neural.fit(X, y)
        metrics["holdout_accuracy"] = "not enough split data"
        metrics["holdout_auc"] = "not enough split data"
        metrics["training_note"] = str(split_exc)[:180]

    bundle = {
        "version": PHASE15_19_VERSION,
        "trained_at": _iso(),
        "model_type": "Fallback feed-forward neural network / sklearn MLPClassifier",
        "feature_columns": feature_columns,
        "model": neural,
        "rows": rows,
        "wins": wins,
        "losses": losses,
        "sources": sources,
        "metrics": metrics,
        "safety": "Advisory only. Can reduce/block weak setups; never forces live orders.",
    }
    _ensure_dirs()
    joblib.dump(bundle, PHASE15_19_NEURAL_FALLBACK_MODEL_FILE)
    meta = {k: v for k, v in bundle.items() if k != "model"}
    meta["fallback_model_file"] = PHASE15_19_NEURAL_FALLBACK_MODEL_FILE
    _write_json(PHASE15_19_NEURAL_META_FILE, meta)
    return {"ok": True, "trained": True, "message": f"Fallback Neural Brain trained from {rows} rows ({wins} wins, {losses} losses). TensorFlow CNN+BiLSTM+Attention was unavailable, so Blue used MLP fallback.", "meta": meta}


def train_neural_network(path: Optional[str] = None, use_imported: bool = True, force: bool = True) -> Dict[str, Any]:
    _ensure_dirs()
    if not _state().get("enabled", True):
        return {"ok": True, "trained": False, "message": "Neural Network Brain is OFF. Use: neural on"}
    if pd is None:
        return {"ok": False, "trained": False, "message": "pandas is missing. Run: pip install pandas"}
    if np is None:
        return {"ok": False, "trained": False, "message": "numpy is missing. Run: pip install numpy"}
    try:
        df, sources = _load_training_frames(path=path, use_imported=use_imported)
    except Exception as e:
        return {"ok": False, "trained": False, "message": f"Could not load training data: {e}"}
    rows = int(len(df)) if df is not None else 0
    if rows <= 0:
        return {"ok": False, "trained": False, "message": "No labeled training rows found. Import MT5/journal/backtest/dataset rows first."}
    wins = int((df["label"].astype(int) == 1).sum())
    losses = int((df["label"].astype(int) == 0).sum())
    if rows < DEFAULT_MIN_ROWS or wins == 0 or losses == 0:
        return {"ok": False, "trained": False, "message": f"Need {DEFAULT_MIN_ROWS}+ labeled rows with both wins and losses. Found {rows} rows ({wins} wins, {losses} losses).", "rows": rows, "wins": wins, "losses": losses}
    if _make_training_matrix is None:
        return {"ok": False, "trained": False, "message": "Training matrix helper unavailable."}
    try:
        X, feature_columns = _make_training_matrix(df)
        y = df["label"].astype(int)
    except Exception as e:
        return {"ok": False, "trained": False, "message": f"Could not build neural training matrix: {e}"}

    tf_ok, tf_msg, _ = _tensorflow_available()
    if tf_ok:
        try:
            res = _train_keras_attention(X, y, feature_columns, rows, wins, losses, sources)
            meta = res.get("meta", {})
            _save_state(last_training_at=meta.get("trained_at"), last_message=res.get("message"), last_result=meta)
            return {**res, "model_file": PHASE15_19_NEURAL_KERAS_MODEL_FILE, "meta_file": PHASE15_19_NEURAL_META_FILE, "rows": rows, "wins": wins, "losses": losses, "metrics": meta.get("metrics", {})}
        except Exception as exc:
            fallback_reason = str(exc)
    else:
        fallback_reason = tf_msg

    res = _train_mlp_fallback(X, y, feature_columns, rows, wins, losses, sources, fallback_reason)
    meta = res.get("meta", {}) if isinstance(res.get("meta"), dict) else {}
    _save_state(last_training_at=meta.get("trained_at"), last_message=res.get("message"), last_result=meta)
    return {**res, "model_file": PHASE15_19_NEURAL_FALLBACK_MODEL_FILE, "meta_file": PHASE15_19_NEURAL_META_FILE, "rows": rows, "wins": wins, "losses": losses, "metrics": meta.get("metrics", {})}


def _load_predictor() -> Optional[Dict[str, Any]]:
    meta = _read_json(PHASE15_19_NEURAL_META_FILE, {})
    if not isinstance(meta, dict) or not meta:
        return None
    model_type = str(meta.get("model_type") or "")
    # Prefer Keras model if meta says it exists.
    if "CNN + BiLSTM" in model_type:
        scaler_file = meta.get("scaler_file")
        model_file = meta.get("keras_model_file") or PHASE15_19_NEURAL_KERAS_MODEL_FILE
        if joblib is None or not scaler_file or not os.path.exists(str(scaler_file)) or not os.path.exists(str(model_file)):
            return None
        ok_tf, _msg, tf = _tensorflow_available()
        if not ok_tf or tf is None:
            return None
        try:
            scaler_bundle = joblib.load(scaler_file)
            model = tf.keras.models.load_model(model_file, compile=False)
            return {"kind": "keras", "model": model, "scaler": scaler_bundle.get("scaler"), "meta": meta, "feature_columns": scaler_bundle.get("feature_columns") or meta.get("feature_columns") or []}
        except Exception:
            return None
    # fallback MLP
    if joblib is None or not os.path.exists(PHASE15_19_NEURAL_FALLBACK_MODEL_FILE):
        return None
    try:
        bundle = joblib.load(PHASE15_19_NEURAL_FALLBACK_MODEL_FILE)
        return {"kind": "mlp", "model": bundle.get("model"), "meta": bundle, "feature_columns": bundle.get("feature_columns") or []}
    except Exception:
        return None


def predict_neural_probability(signal: Dict[str, Any]) -> Dict[str, Any]:
    if not _state().get("enabled", True):
        return {"available": False, "reason": "Neural Network Brain is OFF."}
    if pd is None:
        return {"available": False, "reason": "pandas is not installed."}
    if _signal_to_row is None or _make_training_matrix is None:
        return {"available": False, "reason": "Neural helpers unavailable."}
    predictor = _load_predictor()
    if not predictor:
        return {"available": False, "reason": "No Neural Network Brain model trained yet."}
    try:
        row = pd.DataFrame([_signal_to_row(signal)])
        feature_columns = predictor.get("feature_columns") or []
        X, _ = _make_training_matrix(row, feature_columns=feature_columns)
        if predictor.get("kind") == "keras":
            scaler = predictor.get("scaler")
            if scaler is None:
                return {"available": False, "reason": "Neural scaler unavailable."}
            X_scaled = scaler.transform(X)
            seq_len = int((predictor.get("meta") or {}).get("sequence_length") or PHASE15_19_NEURAL_SEQUENCE_LENGTH or 24)
            X_seq = _matrix_to_sequence(pd.DataFrame(X_scaled, columns=feature_columns), seq_len)
            probability = float(predictor["model"].predict(X_seq, verbose=0).reshape(-1)[0]) * 100.0
        else:
            probability = float(predictor["model"].predict_proba(X)[0][1]) * 100.0
        probability = round(max(0.0, min(100.0, probability)), 1)
        meta = predictor.get("meta") or {}
        return {"available": True, "neural_probability": probability, "trained_at": meta.get("trained_at"), "training_rows": meta.get("rows", 0), "metrics": meta.get("metrics") or {}, "model_type": meta.get("model_type", "Neural Network")}
    except Exception as e:
        return {"available": False, "reason": f"Neural prediction failed: {str(e)[:180]}"}


def apply_neural_network_brain(signal: Dict[str, Any]) -> Dict[str, Any]:
    pred = predict_neural_probability(signal)
    old_conf = _safe_float(signal.get("confidence"), 50)
    engine: Dict[str, Any] = {
        "mode": "not_trained",
        "available": False,
        "old_confidence": old_conf,
        "new_confidence": old_conf,
        "decision": "NO_NEURAL_MODEL",
        "note": pred.get("reason", "No Neural Network Brain model trained yet."),
    }
    if pred.get("available"):
        prob = float(pred.get("neural_probability") or old_conf)
        weight = max(0.0, min(0.6, float(PHASE15_19_NEURAL_CONFIDENCE_BLEND_WEIGHT or 0.30)))
        blended = round(old_conf * (1 - weight) + prob * weight, 1)
        decision = "CONFIRM"
        note = f"Neural probability is {prob}%. Confidence blended from {old_conf}% to {blended}%."
        if prob < float(PHASE15_19_NEURAL_LOW_PROB_BLOCK_THRESHOLD or 42.0) and str(signal.get("action", "WAIT")).upper() in {"BUY", "SELL"}:
            decision = "BLOCK_LOW_NEURAL_PROBABILITY"
            signal["action_before_neural_network"] = signal.get("action")
            signal["action"] = "WAIT"
            note += " Neural brain blocked execution because this setup looks weak compared with learned history."
        engine.update({
            "mode": "trained_neural_network",
            "available": True,
            "neural_probability": prob,
            "old_confidence": old_conf,
            "new_confidence": blended,
            "trained_at": pred.get("trained_at"),
            "training_rows": pred.get("training_rows"),
            "metrics": pred.get("metrics") or {},
            "model_type": pred.get("model_type"),
            "decision": decision,
            "note": note,
        })
        signal["confidence"] = int(max(1, min(95, round(blended))))
    signal["neural_network_brain"] = engine
    return signal


def neural_network_report() -> str:
    st = _state()
    meta = _read_json(PHASE15_19_NEURAL_META_FILE, {})
    model_type = meta.get("model_type", "not trained") if isinstance(meta, dict) else "not trained"
    model_ready = bool(os.path.exists(PHASE15_19_NEURAL_KERAS_MODEL_FILE) or os.path.exists(PHASE15_19_NEURAL_FALLBACK_MODEL_FILE))
    rows = meta.get("rows", "not trained") if isinstance(meta, dict) else "not trained"
    wins = meta.get("wins", "n/a") if isinstance(meta, dict) else "n/a"
    losses = meta.get("losses", "n/a") if isinstance(meta, dict) else "n/a"
    metrics = meta.get("metrics", {}) if isinstance(meta, dict) else {}
    tf_ok, tf_msg, _ = _tensorflow_available()
    return (
        "Phase 15.19 Neural Network Brain Report\n"
        f"Enabled              : {st.get('enabled')}\n"
        f"Background retrain   : {st.get('background_enabled')}\n"
        f"TensorFlow/Keras     : {'available' if tf_ok else 'not available'} ({tf_msg})\n"
        f"Best architecture    : CNN + BiLSTM + Attention\n"
        f"Active model ready   : {model_ready}\n"
        f"Active model type    : {model_type}\n"
        f"Training rows        : {rows}\n"
        f"Wins / Losses        : {wins} / {losses}\n"
        f"Last trained at      : {meta.get('trained_at', 'not trained yet') if isinstance(meta, dict) else 'not trained yet'}\n"
        f"Holdout accuracy     : {metrics.get('holdout_accuracy', 'n/a') if isinstance(metrics, dict) else 'n/a'}\n"
        f"Holdout AUC          : {metrics.get('holdout_auc', 'n/a') if isinstance(metrics, dict) else 'n/a'}\n"
        f"Keras model file     : {PHASE15_19_NEURAL_KERAS_MODEL_FILE}\n"
        f"Fallback model file  : {PHASE15_19_NEURAL_FALLBACK_MODEL_FILE}\n"
        "Behavior             : confirms/reduces/blocks; never forces order punching.\n"
    )


def _last_training_dt() -> Optional[datetime]:
    value = _state().get("last_training_at")
    if not value:
        meta = _read_json(PHASE15_19_NEURAL_META_FILE, {})
        value = meta.get("trained_at") if isinstance(meta, dict) else None
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def run_background_neural_learning_if_due() -> Dict[str, Any]:
    st = _state()
    if not st.get("enabled", True):
        return {"ok": True, "ran": False, "trained": False, "message": "Neural learning skipped: neural brain is OFF."}
    if not st.get("background_enabled", True):
        return {"ok": True, "ran": False, "trained": False, "message": "Neural learning skipped: background retrain is OFF."}
    last = _last_training_dt()
    min_hours = max(1, int(PHASE15_19_NEURAL_MIN_HOURS_BETWEEN_TRAINING or 12))
    if last and _utc_now() - last < timedelta(hours=min_hours):
        return {"ok": True, "ran": False, "trained": False, "message": f"Neural learning not due yet. Next retrain gap: {min_hours}h."}
    res = train_neural_network(path=None, use_imported=True, force=False)
    res["ran"] = True
    return res
