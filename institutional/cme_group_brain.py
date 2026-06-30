"""Phase 16.1 — CME Group Institutional Data Brain.

Safe institutional context layer for Blue.
- Uses local CME snapshots when available.
- Can call an official/user-configured CME API URL when the user has entitlement.
- Never scrapes protected CME pages and never forces orders.
- Adds volume/open-interest/futures sentiment context to Blue signals.
"""
from __future__ import annotations

import csv
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

STATE_FILE = Path("phase16_1_cme_group_brain_state.json")
CONFIG_FILE = Path("institutional/cme_sources.json")
DATA_DIR = Path("datasets/cme")
SNAPSHOT_FILE = DATA_DIR / "cme_context_snapshot.json"

DEFAULT_INTERVAL_SECONDS = 60 * 60 * 6

CME_SYMBOL_MAP = {
    "xauusd": {"contract": "GC", "name": "COMEX Gold Futures", "venue": "COMEX", "blue_symbol": "XAUUSD"},
    "gold": {"contract": "GC", "name": "COMEX Gold Futures", "venue": "COMEX", "blue_symbol": "XAUUSD"},
    "xagusd": {"contract": "SI", "name": "COMEX Silver Futures", "venue": "COMEX", "blue_symbol": "XAGUSD"},
    "silver": {"contract": "SI", "name": "COMEX Silver Futures", "venue": "COMEX", "blue_symbol": "XAGUSD"},
    "usoil": {"contract": "CL", "name": "NYMEX WTI Crude Oil Futures", "venue": "NYMEX", "blue_symbol": "USOIL"},
    "oil": {"contract": "CL", "name": "NYMEX WTI Crude Oil Futures", "venue": "NYMEX", "blue_symbol": "USOIL"},
    "ustec": {"contract": "NQ", "name": "E-mini Nasdaq-100 Futures", "venue": "CME", "blue_symbol": "USTEC"},
    "nasdaq": {"contract": "NQ", "name": "E-mini Nasdaq-100 Futures", "venue": "CME", "blue_symbol": "USTEC"},
    "eurusd": {"contract": "6E", "name": "Euro FX Futures", "venue": "CME", "blue_symbol": "EURUSD"},
    "gbpusd": {"contract": "6B", "name": "British Pound Futures", "venue": "CME", "blue_symbol": "GBPUSD"},
    "usdjpy": {"contract": "6J", "name": "Japanese Yen Futures", "venue": "CME", "blue_symbol": "USDJPY"},
    "btcusd": {"contract": "BTC", "name": "CME Bitcoin Futures", "venue": "CME", "blue_symbol": "BTCUSD"},
    "btc": {"contract": "BTC", "name": "CME Bitcoin Futures", "venue": "CME", "blue_symbol": "BTCUSD"},
    "ethusd": {"contract": "ETH", "name": "CME Ether Futures", "venue": "CME", "blue_symbol": "ETHUSD"},
    "eth": {"contract": "ETH", "name": "CME Ether Futures", "venue": "CME", "blue_symbol": "ETHUSD"},
}

_thread: Optional[threading.Thread] = None
_stop = threading.Event()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_state() -> Dict[str, Any]:
    default = {
        "enabled": True,
        "background": True,
        "running": False,
        "interval_seconds": DEFAULT_INTERVAL_SECONDS,
        "last_run": None,
        "last_message": "CME Institutional Data Brain has not run yet.",
        "last_error": None,
    }
    st = _read_json(STATE_FILE, {})
    if isinstance(st, dict):
        default.update(st)
    return default


def _save_state(**updates: Any) -> Dict[str, Any]:
    st = _read_state()
    st.update(updates)
    st["updated_at"] = _now()
    _write_json(STATE_FILE, st)
    return st


def seed_cme_sources() -> Dict[str, Any]:
    """Create safe config and sample local-data template."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "enabled": True,
        "background": True,
        "interval_seconds": DEFAULT_INTERVAL_SECONDS,
        "mode": "official_api_or_local_file_only",
        "notes": [
            "Use official CME API/DataMine/export files only.",
            "Do not scrape protected CME pages.",
            "Real-time CME data may need licensing/entitlement.",
        ],
        "optional_env": {
            "CME_API_URL": "Official/user-owned endpoint returning JSON context. Leave empty to use local snapshots.",
            "CME_API_KEY": "Optional authorization token if your endpoint requires it.",
        },
        "symbol_map": CME_SYMBOL_MAP,
        "local_csv_template": str(DATA_DIR / "cme_context_manual.csv"),
    }
    _write_json(CONFIG_FILE, cfg)
    csv_path = DATA_DIR / "cme_context_manual.csv"
    if not csv_path.exists():
        csv_path.write_text(
            "blue_symbol,contract,bias,volume_change,open_interest_change,note\n"
            "XAUUSD,GC,neutral,0,0,Add official CME/DataMine values here when available\n"
            "XAGUSD,SI,neutral,0,0,Add official CME/DataMine values here when available\n"
            "USOIL,CL,neutral,0,0,Add official CME/DataMine values here when available\n"
            "USTEC,NQ,neutral,0,0,Add official CME/DataMine values here when available\n"
            "EURUSD,6E,neutral,0,0,Add official CME/DataMine values here when available\n"
            "GBPUSD,6B,neutral,0,0,Add official CME/DataMine values here when available\n"
            "USDJPY,6J,neutral,0,0,Add official CME/DataMine values here when available\n"
            "BTCUSD,BTC,neutral,0,0,Add official CME/DataMine values here when available\n"
            "ETHUSD,ETH,neutral,0,0,Add official CME/DataMine values here when available\n",
            encoding="utf-8",
        )
    if not SNAPSHOT_FILE.exists():
        _write_json(SNAPSHOT_FILE, {"updated_at": _now(), "source": "template", "symbols": {}})
    return {"ok": True, "message": "CME sources seeded. Official/API or local CSV mode ready."}


def _load_local_csv() -> Dict[str, Any]:
    csv_path = DATA_DIR / "cme_context_manual.csv"
    out: Dict[str, Any] = {}
    if not csv_path.exists():
        return out
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sym = str(row.get("blue_symbol") or "").upper().strip()
                if not sym:
                    continue
                out[sym] = {
                    "blue_symbol": sym,
                    "contract": str(row.get("contract") or "").strip(),
                    "bias": str(row.get("bias") or "neutral").lower().strip(),
                    "volume_change": _safe_float(row.get("volume_change")),
                    "open_interest_change": _safe_float(row.get("open_interest_change")),
                    "note": str(row.get("note") or "").strip(),
                }
    except Exception:
        return {}
    return out


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _try_official_api() -> Dict[str, Any]:
    """Optional official/user-owned endpoint.

    Expected JSON shape:
      {"symbols": {"XAUUSD": {"bias":"bullish", "volume_change":12, "open_interest_change":5, "note":"..."}}}
    """
    url = os.getenv("CME_API_URL", "").strip()
    if not url:
        return {}
    try:
        import urllib.request
        req = urllib.request.Request(url)
        key = os.getenv("CME_API_KEY", "").strip()
        if key:
            req.add_header("Authorization", "Bearer " + key)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and isinstance(data.get("symbols"), dict):
            return data.get("symbols") or {}
    except Exception as exc:
        _save_state(last_error="CME API skipped: " + str(exc))
    return {}


def collect_cme_context(force: bool = False) -> Dict[str, Any]:
    seed_cme_sources()
    st = _read_state()
    if not st.get("enabled", True):
        return {"ok": True, "updated": False, "message": "CME Institutional Data Brain is OFF."}
    last = st.get("last_run")
    if last and not force:
        try:
            then = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - then).total_seconds() < int(st.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)):
                return {"ok": True, "updated": False, "message": "CME context not due yet."}
        except Exception:
            pass
    local_symbols = _load_local_csv()
    api_symbols = _try_official_api()
    symbols = dict(local_symbols)
    if isinstance(api_symbols, dict):
        for k, v in api_symbols.items():
            symbols[str(k).upper()] = v
    snapshot = {
        "updated_at": _now(),
        "source": "official_api" if api_symbols else ("local_csv" if local_symbols else "empty_safe_template"),
        "symbols": symbols,
        "note": "CME context is used as confirmation/filter only; never direct execution.",
    }
    _write_json(SNAPSHOT_FILE, snapshot)
    msg = f"CME context refreshed from {snapshot['source']} with {len(symbols)} symbol records."
    _save_state(last_run=_now(), last_message=msg, running=_read_state().get("running", False))
    return {"ok": True, "updated": True, "message": msg, "symbols": len(symbols)}


def _signal_symbol(signal: Dict[str, Any]) -> str:
    raw = str(signal.get("symbol") or signal.get("ticker") or "").lower()
    for key, meta in CME_SYMBOL_MAP.items():
        if key in raw.replace("/", "").replace("=x", ""):
            return str(meta.get("blue_symbol", "")).upper()
    # fallback exact-ish names
    cleaned = raw.upper().replace("=X", "").replace("-USD", "USD")
    if cleaned in {"XAUUSD", "XAGUSD", "USOIL", "USTEC", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"}:
        return cleaned
    return ""


def apply_cme_group_brain(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Attach CME institutional context to a signal automatically."""
    try:
        sym = _signal_symbol(signal)
        if not sym:
            signal["cme_group_brain"] = {"available": False, "note": "No CME futures mapping for this symbol."}
            return signal
        snapshot = _read_json(SNAPSHOT_FILE, {"symbols": {}})
        row = (snapshot.get("symbols") or {}).get(sym) or {}
        meta = next((v for v in CME_SYMBOL_MAP.values() if v.get("blue_symbol") == sym), {})
        action = str(signal.get("action") or "WAIT").upper()
        bias = str(row.get("bias") or "neutral").lower()
        vol = _safe_float(row.get("volume_change"))
        oi = _safe_float(row.get("open_interest_change"))
        confirmation = "neutral"
        delta = 0
        if row:
            if action == "BUY" and bias in {"bullish", "buy", "long"} and (vol >= 0 or oi >= 0):
                confirmation, delta = "supports_buy", 2
            elif action == "SELL" and bias in {"bearish", "sell", "short"} and (vol >= 0 or oi >= 0):
                confirmation, delta = "supports_sell", 2
            elif action in {"BUY", "SELL"} and bias in {"bullish", "bearish", "buy", "sell", "long", "short"}:
                confirmation, delta = "divergence_warning", -2
        old_conf = int(signal.get("confidence") or 0)
        new_conf = max(0, min(100, old_conf + delta))
        if delta:
            signal["confidence"] = new_conf
        note = row.get("note") or "No live/local CME values loaded yet; context is neutral."
        signal["cme_group_brain"] = {
            "available": bool(row),
            "blue_symbol": sym,
            "contract": row.get("contract") or meta.get("contract"),
            "contract_name": meta.get("name"),
            "venue": meta.get("venue"),
            "bias": bias,
            "volume_change": vol,
            "open_interest_change": oi,
            "confirmation": confirmation,
            "confidence_delta": delta,
            "old_confidence": old_conf,
            "new_confidence": new_conf,
            "source": snapshot.get("source"),
            "note": note,
        }
        upgrades = signal.get("smc_upgrade") or []
        if isinstance(upgrades, list) and "CME Group institutional futures context" not in upgrades:
            upgrades.append("CME Group institutional futures context")
            signal["smc_upgrade"] = upgrades
    except Exception as exc:
        signal["cme_group_brain"] = {"available": False, "error": str(exc), "note": "CME layer skipped safely."}
    return signal


def cme_status_text() -> str:
    st = _read_state()
    snap = _read_json(SNAPSHOT_FILE, {"symbols": {}})
    lines = [
        "CME Group Institutional Data Brain",
        f"Enabled       : {st.get('enabled')}",
        f"Background    : {st.get('background')}",
        f"Running       : {st.get('running')}",
        f"Last run      : {st.get('last_run')}",
        f"Last message  : {st.get('last_message')}",
        f"Snapshot src  : {snap.get('source')}",
        f"Symbols loaded: {len((snap.get('symbols') or {}))}",
        "Mapped symbols: XAUUSD/GC, XAGUSD/SI, USOIL/CL, USTEC/NQ, EURUSD/6E, GBPUSD/6B, USDJPY/6J, BTCUSD/BTC, ETHUSD/ETH",
        "Safety        : confirmation/filter only; does not punch orders directly.",
    ]
    if st.get("last_error"):
        lines.append("Last error    : " + str(st.get("last_error")))
    return "\n".join(lines)


def set_cme_brain(enabled: Optional[bool] = None, background: Optional[bool] = None) -> str:
    updates: Dict[str, Any] = {}
    if enabled is not None:
        updates["enabled"] = bool(enabled)
    if background is not None:
        updates["background"] = bool(background)
    st = _save_state(**updates)
    return f"CME Brain enabled={st.get('enabled')} background={st.get('background')}"


def _loop(print_fn: Optional[Callable[[str], None]] = None) -> None:
    _save_state(running=True, started_at=_now(), last_message="CME background worker started.")
    try:
        res = collect_cme_context(force=True)
        if print_fn:
            print_fn("CME Brain: " + str(res.get("message", res)))
    except Exception as exc:
        _save_state(last_error=str(exc), last_message="CME pulse failed safely: " + str(exc))
    while not _stop.wait(60):
        try:
            res = collect_cme_context(force=False)
            if res.get("updated") and print_fn:
                print_fn("CME Brain: " + str(res.get("message", res)))
        except Exception as exc:
            _save_state(last_error=str(exc), last_message="CME pulse failed safely: " + str(exc))
    _save_state(running=False, stopped_at=_now(), last_message="CME background worker stopped.")


def start_cme_group_brain_service(print_fn: Optional[Callable[[str], None]] = None, force: bool = False) -> Dict[str, Any]:
    global _thread
    seed_cme_sources()
    st = _read_state()
    if not st.get("enabled", True) or not st.get("background", True):
        return {"ok": True, "started": False, "message": "CME Institutional Data Brain is OFF."}
    if _thread and _thread.is_alive() and not force:
        return {"ok": True, "started": False, "message": "CME Institutional Data Brain already running."}
    _stop.clear()
    _thread = threading.Thread(target=_loop, kwargs={"print_fn": print_fn}, daemon=True, name="BlueCMEGroupBrain")
    _thread.start()
    return {"ok": True, "started": True, "message": "CME Institutional Data Brain background worker started."}


def stop_cme_group_brain_service() -> Dict[str, Any]:
    _stop.set()
    _save_state(running=False, last_message="CME stop requested.")
    return {"ok": True, "message": "CME Institutional Data Brain stop requested."}
