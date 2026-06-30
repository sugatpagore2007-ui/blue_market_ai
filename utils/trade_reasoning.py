"""Terminal trade-reason cards for Blue Forex Market AI.

This module turns a full signal dictionary into a clean, human-readable reason
block for the terminal. It is intentionally dependency-light so it can be used
from normal analysis, scanner, voice, and autopilot flows without touching MT5.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _safe(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _round(value: Any, digits: int = 2) -> Any:
    try:
        return round(float(value), digits)
    except Exception:
        return value


def _direction_support(signal: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return top supporting and warning notes from MTF analysis."""
    action = _safe(signal.get("action"), "WAIT").upper()
    timeframes = signal.get("timeframes") or {}
    support: List[str] = []
    warnings: List[str] = []
    order = ["1d", "4h", "1h", "15m", "5m", "3m", "1m"]
    for tf in order:
        data = timeframes.get(tf) or {}
        if not data:
            continue
        score = float(data.get("score") or 0)
        why = ", ".join((data.get("why") or [])[:3])
        if action == "BUY":
            if score > 0:
                support.append(f"{tf}: bullish score {score:g} — {why}")
            elif score < 0:
                warnings.append(f"{tf}: bearish conflict {score:g} — {why}")
        elif action == "SELL":
            if score < 0:
                support.append(f"{tf}: bearish score {score:g} — {why}")
            elif score > 0:
                warnings.append(f"{tf}: bullish conflict {score:g} — {why}")
        else:
            if abs(score) < 1.6:
                warnings.append(f"{tf}: weak/mixed score {score:g} — {why}")
            elif score > 0:
                support.append(f"{tf}: bullish pressure {score:g} — {why}")
            else:
                support.append(f"{tf}: bearish pressure {score:g} — {why}")
    return support[:4], warnings[:4]


def _rr_ratio(signal: Dict[str, Any]) -> float:
    action = _safe(signal.get("action"), "WAIT").upper()
    try:
        entry = float(signal.get("entry") or 0)
        stop = float(signal.get("stop_loss") or 0)
        t2 = float(signal.get("target_2") or signal.get("target_1") or 0)
        risk = abs(entry - stop)
        reward = abs(t2 - entry)
        if action == "WAIT" or risk <= 0:
            return 0.0
        return round(reward / risk, 2)
    except Exception:
        return 0.0


def build_terminal_reason_card(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured reason card showing the basis of the trade/no-trade."""
    action = _safe(signal.get("action"), "WAIT").upper()
    confidence = signal.get("confidence", 0)
    support, warnings = _direction_support(signal)
    market_context = signal.get("market_context") or {}
    macro = signal.get("macro_brain") or {}
    news = signal.get("news_filter") or {}
    candle = signal.get("candlestick_brain") or {}
    dataset = signal.get("dataset_ml_engine") or {}
    video = signal.get("video_knowledge_engine") or {}
    no_trade = signal.get("no_trade_intelligence") or {}
    aplus = signal.get("a_plus_filter") or {}
    tf = _safe(signal.get("entry_timeframe"), "5m")
    regime = _safe(signal.get("regime"), _safe(market_context.get("regime"), "unknown"))
    session = _safe(signal.get("session"), "unknown")
    session_note = _safe(signal.get("session_note"), "")

    if action == "WAIT":
        final_decision = "WAIT / NO TRADE"
        main_basis = "Blue is skipping this setup because the final confluence is not strong enough after filters."
    else:
        final_decision = f"{action} SETUP FOUND"
        main_basis = f"Blue selected {action} because multi-timeframe direction, SMC/price-action context, and risk plan are aligned enough for the current mode."

    filters: List[str] = []
    if news:
        filters.append(f"News: {_safe(news.get('status'), 'checked')} | penalty {news.get('penalty', 0)} | {_safe(news.get('note'), '')}")
    if macro:
        filters.append(f"Macro: {_safe(macro.get('bias'), macro.get('decision', 'neutral'))} | {_safe(macro.get('note'), '')}")
    if candle:
        filters.append(
            f"Candles: {_safe(candle.get('bias'), 'neutral')} | decision {_safe(candle.get('decision'), 'advisory')} | top {', '.join([_safe(p.get('name')) for p in (candle.get('top_patterns') or [])[:2]])}"
        )
    if dataset:
        if dataset.get("available"):
            filters.append(f"Dataset ML: {dataset.get('dataset_probability')}% probability | {dataset.get('decision')} | {_safe(dataset.get('note'), '')}")
        else:
            filters.append(f"Dataset ML: not trained/insufficient data | {_safe(dataset.get('note'), '')}")
    if video:
        filters.append(f"Strategy knowledge: {video.get('decision')} | delta {video.get('confidence_delta', 0)} | {_safe(video.get('note'), '')}")
    if no_trade:
        filters.append(f"No-trade brain: {_safe(no_trade.get('decision'), 'checked')} | {_safe(no_trade.get('note'), '')}")
    if aplus:
        filters.append(f"A+ filter: {'PASS' if aplus.get('allow_autopilot') else 'BLOCK'} | {_safe(aplus.get('reason'), '')}")

    risk = signal.get("risk") or {}
    lot = risk.get("recommended_lot_size", 0)
    rr = _rr_ratio(signal)

    return {
        "final_decision": final_decision,
        "action": action,
        "confidence": confidence,
        "main_basis": main_basis,
        "entry_basis": {
            "entry_timeframe": tf,
            "session": session,
            "session_note": session_note,
            "regime": regime,
            "entry": signal.get("entry"),
            "stop_loss": signal.get("stop_loss"),
            "target_1": signal.get("target_1"),
            "target_2": signal.get("target_2"),
            "rr_to_target_2": rr,
            "lot_size": lot,
        },
        "supporting_reasons": support,
        "warning_reasons": warnings,
        "filters": filters[:8],
        "analyst_summary": _safe(signal.get("analyst_reason") or signal.get("human_read"), "No analyst summary generated."),
    }


def attach_terminal_reason_card(signal: Dict[str, Any]) -> Dict[str, Any]:
    signal = dict(signal)
    signal["terminal_reason_card"] = build_terminal_reason_card(signal)
    return signal


def format_terminal_reason_card(signal: Dict[str, Any]) -> str:
    card = signal.get("terminal_reason_card") or build_terminal_reason_card(signal)
    entry = card.get("entry_basis") or {}
    lines: List[str] = []
    lines.append("\nTRADE BASIS / REASON CARD")
    lines.append("-" * 72)
    lines.append(f"Final decision : {card.get('final_decision')} | Confidence: {card.get('confidence')}%")
    lines.append(f"Main basis     : {card.get('main_basis')}")
    lines.append(
        "Entry basis    : "
        f"TF {entry.get('entry_timeframe')} | Session {entry.get('session')} | Regime {entry.get('regime')}"
    )
    if entry.get("session_note"):
        lines.append(f"Session note   : {entry.get('session_note')}")
    lines.append(
        "Risk plan      : "
        f"Entry {entry.get('entry')} | SL {entry.get('stop_loss')} | T1 {entry.get('target_1')} | T2 {entry.get('target_2')} | RR(T2) {entry.get('rr_to_target_2')} | Lot {entry.get('lot_size')}"
    )
    support = card.get("supporting_reasons") or []
    warnings = card.get("warning_reasons") or []
    filters = card.get("filters") or []
    if support:
        lines.append("Why trade      :")
        for item in support[:4]:
            lines.append(f"  + {item}")
    if warnings:
        lines.append("Warnings       :")
        for item in warnings[:4]:
            lines.append(f"  ! {item}")
    if filters:
        lines.append("Filters checked:")
        for item in filters[:8]:
            lines.append(f"  - {item}")
    lines.append("-" * 72)
    return "\n".join(lines)
