"""Trade style detection for Blue Market AI.
Default style is Intraday. Other styles are used only if the user asks for them.
"""
from __future__ import annotations

from config import DEFAULT_TRADE_STYLE, TRADE_STYLE_PROFILES

STYLE_KEYWORDS = {
    "scalping": ["scalp", "scalping", "quick scalp", "scalper"],
    "swing": ["swing", "swing trade", "swing trading"],
    "position": ["position", "position trade", "position trading", "positional"],
    "intraday": ["intraday", "intra day", "day trade", "day trading"],
}

def detect_trade_style(text: str) -> str:
    t = (text or "").lower()
    for style, words in STYLE_KEYWORDS.items():
        if any(w in t for w in words):
            return style
    return DEFAULT_TRADE_STYLE

def style_label(style: str) -> str:
    return TRADE_STYLE_PROFILES.get(style, TRADE_STYLE_PROFILES[DEFAULT_TRADE_STYLE]).get("label", style.title())

def strip_style_words(text: str) -> str:
    out = text or ""
    for words in STYLE_KEYWORDS.values():
        for w in sorted(words, key=len, reverse=True):
            out = out.replace(w, " ")
    return " ".join(out.split())
