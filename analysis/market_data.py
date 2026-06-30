from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any, Dict, Tuple

import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from config import (
        CHART_DATA_SOURCE,
        CHART_DATA_SOURCE_STATE_FILE,
        MT5_CHART_DATA_ENABLED,
        MT5_CHART_DATA_FALLBACK_TO_YAHOO,
        MT5_CHART_MAX_BARS,
        MT5_CHART_MIN_BARS,
    )
except Exception:
    CHART_DATA_SOURCE = "auto"
    CHART_DATA_SOURCE_STATE_FILE = "chart_data_source_state.json"
    MT5_CHART_DATA_ENABLED = True
    MT5_CHART_DATA_FALLBACK_TO_YAHOO = True
    MT5_CHART_MAX_BARS = 5000
    MT5_CHART_MIN_BARS = 80

try:
    from mt5_bridge.terminal import mt5, ensure_connected, select_symbol, map_symbol
except Exception:
    mt5 = None
    ensure_connected = None
    select_symbol = None
    map_symbol = None

VALID_DATA_SOURCES = {"auto", "mt5", "yahoo"}


def _state_file() -> Path:
    return Path(CHART_DATA_SOURCE_STATE_FILE)


def get_chart_data_source() -> str:
    """Return selected chart data source: auto, mt5, or yahoo."""
    default = str(CHART_DATA_SOURCE or "auto").lower().strip()
    if default not in VALID_DATA_SOURCES:
        default = "auto"
    try:
        p = _state_file()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            src = str(data.get("source", default)).lower().strip()
            if src in VALID_DATA_SOURCES:
                return src
    except Exception:
        pass
    return default


def set_chart_data_source(source: str) -> str:
    """Persist chart data source choice."""
    src = str(source or "auto").lower().strip()
    aliases = {
        "broker": "mt5",
        "terminal": "mt5",
        "metatrader": "mt5",
        "yf": "yahoo",
        "yfinance": "yahoo",
        "fallback": "auto",
    }
    src = aliases.get(src, src)
    if src not in VALID_DATA_SOURCES:
        src = "auto"
    payload = {
        "source": src,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "auto = MT5 first then Yahoo fallback; mt5 = broker candles only; yahoo = yfinance only",
    }
    _state_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return src


def _parse_period_to_days(period: str) -> int:
    p = str(period or "5d").lower().strip()
    m = re.match(r"^(\d+)([a-z]+)$", p)
    if not m:
        return 30
    n = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("d"):
        return max(1, n)
    if unit.startswith("w"):
        return max(1, n * 7)
    if unit.startswith("mo") or unit.startswith("m"):
        return max(1, n * 30)
    if unit.startswith("y"):
        return max(1, n * 365)
    return max(1, n)


def _interval_to_minutes(interval: str) -> int:
    i = str(interval or "5m").lower().strip()
    if i.endswith("m"):
        return max(1, int(i[:-1] or 5))
    if i.endswith("h"):
        return max(1, int(i[:-1] or 1)) * 60
    if i.endswith("d"):
        return max(1, int(i[:-1] or 1)) * 60 * 24
    return 5


def _period_interval_to_count(period: str, interval: str) -> int:
    days = _parse_period_to_days(period)
    mins = _interval_to_minutes(interval)
    count = int((days * 24 * 60) / max(mins, 1))
    # Add buffer for weekend/market gaps but cap for performance.
    count = int(count * 1.4) + 50
    count = max(int(MT5_CHART_MIN_BARS), count)
    count = min(int(MT5_CHART_MAX_BARS), count)
    return count


def _mt5_timeframe(interval: str):
    if mt5 is None:
        return None
    i = str(interval or "5m").lower().strip()
    mapping = {
        "1m": getattr(mt5, "TIMEFRAME_M1", None),
        "2m": getattr(mt5, "TIMEFRAME_M2", None),
        "3m": getattr(mt5, "TIMEFRAME_M3", None),
        "4m": getattr(mt5, "TIMEFRAME_M4", None),
        "5m": getattr(mt5, "TIMEFRAME_M5", None),
        "6m": getattr(mt5, "TIMEFRAME_M6", None),
        "10m": getattr(mt5, "TIMEFRAME_M10", None),
        "12m": getattr(mt5, "TIMEFRAME_M12", None),
        "15m": getattr(mt5, "TIMEFRAME_M15", None),
        "20m": getattr(mt5, "TIMEFRAME_M20", None),
        "30m": getattr(mt5, "TIMEFRAME_M30", None),
        "1h": getattr(mt5, "TIMEFRAME_H1", None),
        "2h": getattr(mt5, "TIMEFRAME_H2", None),
        "3h": getattr(mt5, "TIMEFRAME_H3", None),
        "4h": getattr(mt5, "TIMEFRAME_H4", None),
        "1d": getattr(mt5, "TIMEFRAME_D1", None),
        "d": getattr(mt5, "TIMEFRAME_D1", None),
        "daily": getattr(mt5, "TIMEFRAME_D1", None),
    }
    return mapping.get(i, getattr(mt5, "TIMEFRAME_M5", None))


def _normalize_ohlcv(df: pd.DataFrame, *, source: str, symbol: str, broker_symbol: str | None = None) -> pd.DataFrame:
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns: {missing}")
    df = df.dropna(subset=required).copy()
    if "volume" not in df.columns:
        df["volume"] = 0
    # Convert to numeric where possible.
    for col in ["open", "high", "low", "close", "volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0 if col not in required else df[col])
    df.attrs["data_source"] = source
    df.attrs["symbol"] = symbol
    if broker_symbol:
        df.attrs["broker_symbol"] = broker_symbol
    return df


def fetch_yahoo_ohlcv(ticker: str, interval: str, period: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is not installed. Run: pip install -r requirements.txt")
    df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError(f"No Yahoo/yfinance data returned for {ticker} {interval}/{period}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns={c: c.lower().replace(" ", "_") for c in df.columns})
    return _normalize_ohlcv(df, source="yahoo", symbol=ticker)


def fetch_mt5_ohlcv(ticker: str, interval: str, period: str) -> pd.DataFrame:
    if not MT5_CHART_DATA_ENABLED:
        raise RuntimeError("MT5 chart data is disabled in config.py")
    if mt5 is None:
        raise RuntimeError("MetaTrader5 package is not installed. Run: pip install MetaTrader5")
    if ensure_connected is None or select_symbol is None:
        raise RuntimeError("MT5 bridge is not available")
    ok, msg = ensure_connected()
    if not ok:
        raise RuntimeError(msg)
    ok_sel, broker_symbol = select_symbol(ticker)
    if not ok_sel:
        mapped = map_symbol(ticker) if map_symbol else ticker
        raise RuntimeError(f"Could not select MT5 symbol for {ticker}. Tried {mapped}. Use: show mt5 symbols xau / eur / btc")
    tf = _mt5_timeframe(interval)
    if tf is None:
        raise RuntimeError(f"Unsupported MT5 timeframe: {interval}")
    count = _period_interval_to_count(period, interval)
    rates = mt5.copy_rates_from_pos(broker_symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        err = mt5.last_error()
        raise RuntimeError(f"No MT5 candles returned for {broker_symbol} {interval}. MT5 last_error={err}")
    df = pd.DataFrame(rates)
    if df.empty:
        raise RuntimeError(f"Empty MT5 candles for {broker_symbol} {interval}")
    # MT5 returns unix seconds in local terminal/server context. UTC conversion is safest for pandas logic.
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    df = df.rename(columns={"tick_volume": "volume"})
    df = _normalize_ohlcv(df, source="mt5", symbol=ticker, broker_symbol=broker_symbol)
    if len(df) < int(MT5_CHART_MIN_BARS):
        raise RuntimeError(f"Only {len(df)} MT5 bars returned for {broker_symbol}; need at least {MT5_CHART_MIN_BARS}")
    return df


def fetch_ohlcv(ticker: str, interval: str, period: str) -> pd.DataFrame:
    """Fetch OHLCV candles using configured data priority.

    Phase 15.14 behavior:
    - auto: MT5 broker candles first, Yahoo fallback if MT5 is not connected/unavailable.
    - mt5: MT5 broker candles only.
    - yahoo: Yahoo/yfinance candles only.
    """
    source = get_chart_data_source()
    if source == "yahoo":
        return fetch_yahoo_ohlcv(ticker, interval, period)

    if source in {"auto", "mt5"}:
        try:
            return fetch_mt5_ohlcv(ticker, interval, period)
        except Exception as mt5_exc:
            if source == "mt5" or not MT5_CHART_DATA_FALLBACK_TO_YAHOO:
                raise
            df = fetch_yahoo_ohlcv(ticker, interval, period)
            df.attrs["data_source"] = "yahoo_fallback"
            df.attrs["mt5_error"] = str(mt5_exc)
            return df

    return fetch_yahoo_ohlcv(ticker, interval, period)


def chart_data_source_status_text() -> str:
    src = get_chart_data_source()
    mode_line = {
        "auto": "AUTO — MT5 broker candles first, Yahoo/yfinance fallback if MT5 data is unavailable.",
        "mt5": "MT5 ONLY — Blue analyzes connected broker candles only.",
        "yahoo": "YAHOO ONLY — Blue uses old yfinance candles.",
    }.get(src, src)
    mt5_status = "not checked"
    if mt5 is None:
        mt5_status = "MetaTrader5 package missing"
    else:
        try:
            ok, msg = ensure_connected() if ensure_connected else (False, "MT5 bridge unavailable")
            mt5_status = ("connected — " + msg) if ok else ("not connected — " + msg)
        except Exception as exc:
            mt5_status = "not connected — " + str(exc)
    return (
        "Chart Data Source\n"
        f"Mode        : {mode_line}\n"
        f"MT5 status  : {mt5_status}\n"
        "Commands    : use mt5 data | use yahoo data | use auto data | mt5 candles gold | compare data gold"
    )


def mt5_candles_test_text(ticker: str, label: str = "symbol", interval: str = "5m", period: str = "5d") -> str:
    try:
        df = fetch_mt5_ohlcv(ticker, interval, period)
        last = df.iloc[-1]
        return (
            f"MT5 Candle Test: {label}\n"
            f"Broker symbol : {df.attrs.get('broker_symbol', ticker)}\n"
            f"Timeframe     : {interval} | bars: {len(df)}\n"
            f"Latest candle : O {round(float(last['open']), 6)} | H {round(float(last['high']), 6)} | "
            f"L {round(float(last['low']), 6)} | C {round(float(last['close']), 6)}\n"
            f"Source        : MT5 broker candles"
        )
    except Exception as exc:
        return f"MT5 candle test failed for {label}: {exc}"


def compare_mt5_yahoo_text(ticker: str, label: str = "symbol", interval: str = "5m", period: str = "5d") -> str:
    lines = [f"Data Source Comparison: {label}", f"Timeframe: {interval} | Period: {period}"]
    mt5_close = None
    yahoo_close = None
    try:
        mdf = fetch_mt5_ohlcv(ticker, interval, period)
        ml = mdf.iloc[-1]
        mt5_close = float(ml["close"])
        lines.append(f"MT5   : {mdf.attrs.get('broker_symbol', ticker)} close {round(mt5_close, 6)} | bars {len(mdf)}")
    except Exception as exc:
        lines.append(f"MT5   : unavailable — {exc}")
    try:
        ydf = fetch_yahoo_ohlcv(ticker, interval, period)
        yl = ydf.iloc[-1]
        yahoo_close = float(yl["close"])
        lines.append(f"Yahoo : {ticker} close {round(yahoo_close, 6)} | bars {len(ydf)}")
    except Exception as exc:
        lines.append(f"Yahoo : unavailable — {exc}")
    if mt5_close is not None and yahoo_close is not None:
        diff = mt5_close - yahoo_close
        pct = (diff / yahoo_close * 100.0) if yahoo_close else 0.0
        lines.append(f"Diff  : {round(diff, 6)} ({round(pct, 4)}%)")
        lines.append("Best practice: use MT5 data for autopilot because order execution also happens on MT5.")
    return "\n".join(lines)
