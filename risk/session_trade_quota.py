"""Phase 15.27 Gold-Reserved Daily Trade Quota.

Final rule requested by user:
- max 2 Blue auto entries per day
- auto entries only during London or New York session
- 1 daily slot is reserved for Gold/XAUUSD only
- 1 daily slot is reserved for all other symbols
- if Blue does not trade in London, New York can still take only 2 trades total:
  one Gold trade and one non-Gold trade
- Gold trade needs stronger quality: A+ setup OR 100% confidence
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, time
from pathlib import Path
from typing import Any, Dict

STATE_FILE = Path("phase15_22_session_trade_quota_state.json")

DEFAULTS = {
    "enabled": True,
    "max_daily_trades": 2,
    "gold_daily_limit": 1,
    "other_daily_limit": 1,
    "gold_requires_a_plus_or_100": True,
    "london_utc_start": "07:00",
    "london_utc_end": "16:00",
    "ny_utc_start": "12:00",
    "ny_utc_end": "21:00",
}


def _load() -> Dict[str, Any]:
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        out = dict(DEFAULTS)
        out.update(d)
        return out
    except Exception:
        return dict(DEFAULTS)


def _save(d: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def _today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _hhmm_to_time(s: str) -> time:
    h, m = str(s).split(":")[:2]
    return time(int(h), int(m))


def _in_window(now_t: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now_t < end
    return now_t >= start or now_t < end


def current_session(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    utc_t = now.astimezone(timezone.utc).time()
    cfg = _load()
    in_ld = _in_window(utc_t, _hhmm_to_time(cfg["london_utc_start"]), _hhmm_to_time(cfg["london_utc_end"]))
    in_ny = _in_window(utc_t, _hhmm_to_time(cfg["ny_utc_start"]), _hhmm_to_time(cfg["ny_utc_end"]))
    # Overlap should be treated as NY after NY starts.
    if in_ny:
        return "new_york"
    if in_ld:
        return "london"
    return "outside_session"


def _is_gold_symbol(symbol: Any) -> bool:
    s = str(symbol or "").upper().replace("/", "").replace("-", "").replace("_", "")
    return "XAU" in s or "GOLD" in s or "GC=F" in s


def _grade_from_signal(signal: Dict[str, Any] | None) -> str:
    if not signal:
        return ""
    g = signal.get("trade_quality_grades") or {}
    for key in ("overall", "setup", "execution"):
        if g.get(key):
            return str(g.get(key)).upper().strip()
    return str(signal.get("grade") or signal.get("setup_grade") or "").upper().strip()


def _gold_quality_ok(signal: Dict[str, Any] | None) -> bool:
    if not signal:
        return False
    grade = _grade_from_signal(signal)
    try:
        confidence = float(signal.get("confidence") or 0)
    except Exception:
        confidence = 0.0
    return grade in {"A+", "A PLUS", "APLUS"} or confidence >= 100.0


def _day_state(cfg: Dict[str, Any]) -> Dict[str, Any]:
    key = _today_key()
    days = cfg.setdefault("days", {})
    day = days.setdefault(key, {
        "total": 0,
        "gold": 0,
        "other": 0,
        "london": 0,
        "new_york": 0,
        "outside_session": 0,
        "trades": [],
    })
    # Backward-compatible keys if an old state file exists.
    day.setdefault("gold", 0)
    day.setdefault("other", 0)
    day.setdefault("london", 0)
    day.setdefault("new_york", 0)
    day.setdefault("outside_session", 0)
    day.setdefault("trades", [])
    cfg["days"] = {key: day}
    return day


def can_place_trade(session: str | None = None, symbol: Any = None, signal: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = _load()
    if not cfg.get("enabled", True):
        return {"ok": True, "message": "Session/category quota disabled.", "session": session or current_session()}
    session = session or current_session()
    day = _day_state(cfg)
    total = int(day.get("total", 0) or 0)
    if session not in {"london", "new_york"}:
        return {"ok": False, "message": "Auto entries allowed only during London or New York session by Phase 15.27 quota.", "session": session, "day": day}
    if total >= int(cfg.get("max_daily_trades", 2)):
        return {"ok": False, "message": f"Daily quota reached: {total}/{cfg.get('max_daily_trades')} trades used.", "session": session, "day": day}

    is_gold = _is_gold_symbol(symbol or (signal or {}).get("symbol") or (signal or {}).get("ticker"))
    category = "gold" if is_gold else "other"
    if is_gold:
        used = int(day.get("gold", 0) or 0)
        if used >= int(cfg.get("gold_daily_limit", 1)):
            return {"ok": False, "message": f"Gold reserved slot already used: {used}/{cfg.get('gold_daily_limit')}.", "session": session, "category": category, "day": day}
        if cfg.get("gold_requires_a_plus_or_100", True) and not _gold_quality_ok(signal):
            grade = _grade_from_signal(signal)
            conf = (signal or {}).get("confidence", 0)
            return {"ok": False, "message": f"Gold slot requires A+ setup or 100% confidence. Current grade={grade or 'unknown'}, confidence={conf}%.", "session": session, "category": category, "day": day}
    else:
        used = int(day.get("other", 0) or 0)
        if used >= int(cfg.get("other_daily_limit", 1)):
            return {"ok": False, "message": f"Other-pair slot already used: {used}/{cfg.get('other_daily_limit')}.", "session": session, "category": category, "day": day}

    return {"ok": True, "message": f"Phase 15.27 quota OK: {category} slot available in {session}. Daily total {total}/{cfg.get('max_daily_trades')}.", "session": session, "category": category, "day": day}


def record_trade(symbol: str, action: str, session: str | None = None, ticket: Any = None, signal: Dict[str, Any] | None = None) -> None:
    cfg = _load()
    session = session or current_session()
    day = _day_state(cfg)
    category = "gold" if _is_gold_symbol(symbol or (signal or {}).get("symbol") or (signal or {}).get("ticker")) else "other"
    day["total"] = int(day.get("total", 0) or 0) + 1
    day[session] = int(day.get(session, 0) or 0) + 1
    day[category] = int(day.get(category, 0) or 0) + 1
    day.setdefault("trades", []).append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "session": session,
        "category": category,
        "symbol": symbol,
        "action": action,
        "ticket": str(ticket or ""),
    })
    _save(cfg)


def quota_status_text() -> str:
    cfg = _load()
    day = _day_state(cfg)
    _save(cfg)
    session = current_session()
    return "\n".join([
        "Phase 15.27 Gold/Other Reserved Trade Quota",
        f"Enabled          : {cfg.get('enabled')}",
        f"Current session  : {session}",
        f"Daily limit      : {day.get('total', 0)}/{cfg.get('max_daily_trades')}",
        f"Gold slot        : {day.get('gold', 0)}/{cfg.get('gold_daily_limit')} (A+ or 100% required)",
        f"Other slot       : {day.get('other', 0)}/{cfg.get('other_daily_limit')}",
        f"London used      : {day.get('london', 0)}",
        f"New York used    : {day.get('new_york', 0)}",
        "Rule             : Max 2/day total = 1 Gold slot + 1 other-pair slot. If London has no trade, NY can still take only these same 2 slots.",
    ])
