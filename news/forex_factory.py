from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re
import requests
from bs4 import BeautifulSoup
from config import FOREX_FACTORY_URL, NEWS_LOOKAHEAD_HOURS

CURRENCY_MAP = {
    "GC=F": ["USD"], "SI=F": ["USD"], "EURUSD=X": ["EUR", "USD"], "GBPUSD=X": ["GBP", "USD"],
    "JPY=X": ["USD", "JPY"], "BTC-USD": ["USD"], "ETH-USD": ["USD"], "CL=F": ["USD"],
    "NQ=F": ["USD"], "ES=F": ["USD"], "DX-Y.NYB": ["USD"],
}

HIGH_WORDS = ("High", "red", "FOMC", "CPI", "NFP", "Non-Farm", "Interest Rate", "Powell", "GDP", "PPI")

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def get_forex_factory_events(ticker: str, hours: int = NEWS_LOOKAHEAD_HOURS):
    """Best-effort Forex Factory calendar parser. If blocked/changed, returns safe fallback."""
    currencies = CURRENCY_MAP.get(ticker, ["USD"])
    try:
        headers = {"User-Agent": "Mozilla/5.0 BlueMarketAI/5.0"}
        r = requests.get(FOREX_FACTORY_URL, headers=headers, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = _clean(soup.get_text(" "))
        events = []
        # Robust fallback parser: scan lines for relevant currencies and high-impact keywords.
        for cur in currencies:
            pattern = rf"({cur}).{{0,120}}({'|'.join(map(re.escape, HIGH_WORDS))}).{{0,160}}"
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                events.append({"currency": cur, "impact": "High", "title": _clean(m.group(0))[:180], "source": "Forex Factory"})
        # De-duplicate
        seen, out = set(), []
        for e in events[:8]:
            key = (e["currency"], e["title"][:60])
            if key not in seen:
                seen.add(key); out.append(e)
        return out
    except Exception as exc:
        return [{"currency": ",".join(currencies), "impact": "Unknown", "title": f"Forex Factory unavailable or blocked: {exc}", "source": "Forex Factory"}]

def news_filter(ticker: str):
    events = get_forex_factory_events(ticker)
    blocked = any(e.get("impact") == "High" for e in events)
    if blocked:
        note = "High-impact Forex Factory news found for this symbol currency. Avoid entry near news or reduce risk."
        penalty = -8
    elif events and "unavailable" in events[0].get("title", "").lower():
        note = "Forex Factory could not be checked. Manually check calendar before entry."
        penalty = -3
    else:
        note = "No high-impact Forex Factory warning detected by parser."
        penalty = 0
    return {"blocked": blocked, "penalty": penalty, "note": note, "events": events[:5]}
