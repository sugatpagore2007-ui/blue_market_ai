"""Macro/news context layer for Blue Human Trader Brain.

This module is intentionally defensive. It never pretends a web calendar is
perfect; it converts available calendar/sentiment info into a trading caution
object that the no-trade engine can use.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

try:
    from config import MACRO_BRAIN_CONFIG
except Exception:
    MACRO_BRAIN_CONFIG = {
        "high_impact_keywords": ["CPI", "NFP", "FOMC", "Interest Rate"],
        "usd_sensitive": [],
        "manual_calendar_note": "Check live economic calendar manually.",
    }

CURRENCY_BY_TICKER = {
    "GC=F": ["USD"], "SI=F": ["USD"], "EURUSD=X": ["EUR", "USD"],
    "GBPUSD=X": ["GBP", "USD"], "JPY=X": ["USD", "JPY"],
    "BTC-USD": ["USD"], "ETH-USD": ["USD"], "CL=F": ["USD"],
    "NQ=F": ["USD"], "ES=F": ["USD"], "DX-Y.NYB": ["USD"],
}

def _event_text(event: Dict[str, Any]) -> str:
    return " ".join(str(event.get(k, "")) for k in ("currency", "impact", "title", "source"))

def build_macro_brain(ticker: str, news: Dict[str, Any] | None = None, sentiment: Dict[str, Any] | None = None) -> Dict[str, Any]:
    news = news or {}
    sentiment = sentiment or {}
    keywords = [k.lower() for k in MACRO_BRAIN_CONFIG.get("high_impact_keywords", [])]
    currencies = CURRENCY_BY_TICKER.get(ticker, ["USD"])
    events: List[Dict[str, Any]] = list(news.get("events") or [])

    high_events = []
    unknown_events = []
    for event in events:
        text = _event_text(event).lower()
        impact = str(event.get("impact", "")).lower()
        if "unknown" in impact or "unavailable" in text or "blocked" in text:
            unknown_events.append(event)
        if "high" in impact or any(k in text for k in keywords):
            high_events.append(event)

    notes = []
    risk_score = 0
    if high_events or news.get("blocked"):
        risk_score += 35
        notes.append("High-impact macro/news risk is detected for this symbol currency.")
    if unknown_events or "unavailable" in str(news.get("note", "")).lower():
        risk_score += 15
        notes.append("Live calendar could not be verified, so manual calendar check is required.")
    if ticker in MACRO_BRAIN_CONFIG.get("usd_sensitive", []):
        notes.append("This symbol is USD-sensitive; DXY/Fed news can change direction quickly.")
    if sentiment.get("sentiment") in {"greed", "fear"}:
        risk_score += 5
        notes.append(sentiment.get("note", "Sentiment is extreme; avoid chasing late moves."))

    if not notes:
        notes.append("No strong macro warning was detected by available sources.")

    bias = "risk_off" if high_events else "neutral"
    return {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "currencies": currencies,
        "bias": bias,
        "risk_score": min(100, risk_score),
        "high_impact_events": high_events[:5],
        "unknown_events": unknown_events[:3],
        "note": " ".join(notes),
        "manual_calendar_note": MACRO_BRAIN_CONFIG.get("manual_calendar_note", "Check the economic calendar manually."),
    }
