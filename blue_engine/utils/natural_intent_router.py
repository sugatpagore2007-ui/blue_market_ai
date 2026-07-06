"""Phase 15.21 Natural Intent Brain.

This layer is additive. It does not remove fixed commands. It reads normal human
phrases and routes them into the same safe internal commands Blue already uses.
Dangerous execution actions stay protected by existing order/risk safety.
"""
from __future__ import annotations

import re
from typing import List

# Canonical symbol words used by the natural router.
_SYMBOL_ALIASES = {
    "gold": "gold", "xau": "gold", "xauusd": "gold", "xau/usd": "gold",
    "btc": "btc", "bitcoin": "btc", "btcusd": "btc",
    "eth": "eth", "ethereum": "eth", "ethusd": "eth",
    "eur": "eurusd", "euro": "eurusd", "eurusd": "eurusd", "euro dollar": "eurusd",
    "gbp": "gbpusd", "pound": "gbpusd", "gbpusd": "gbpusd", "cable": "gbpusd",
    "jpy": "usdjpy", "yen": "usdjpy", "usdjpy": "usdjpy", "usd jpy": "usdjpy",
    "silver": "silver", "xag": "silver", "xag usd": "silver", "xagusd": "silver",
    "oil": "usoil", "us oil": "usoil", "wti": "usoil", "crude": "usoil",
    "ustec": "ustec", "us tech": "ustec", "us tech 100": "ustec", "nasdaq": "nasdaq", "nas100": "nasdaq", "us100": "nasdaq",
    "spx": "spx", "sp500": "spx", "s&p 500": "spx", "us500": "spx",
}


def _clean(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.replace("blue,", "").replace("blue ", "")
    text = re.sub(r"[^a-z0-9/&% ._-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _symbol(text: str) -> str:
    # Longer aliases first.
    for k in sorted(_SYMBOL_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text):
            return _SYMBOL_ALIASES[k]
    return ""


def _has_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def infer_intent_commands(text: str) -> List[str]:
    """Return one or more canonical commands, or [] when no natural intent match."""
    t = _clean(text)
    if not t:
        return []
    sym = _symbol(t)

    # Emergency/control language.
    if _has_any(t, ["stop everything", "stop all", "pause everything", "turn everything off", "stop the bot", "kill auto"]):
        return ["stop everything"]
    if _has_any(t, ["start everything", "run full auto", "start full auto", "automatic mode on", "make everything automatic"]):
        return ["full auto on"]
    if _has_any(t, ["is blue running", "what is running", "system ok", "show system", "full status", "health check"]):
        return ["status"]

    # Natural market analysis.
    if sym:
        if _has_any(t, ["what is", "what's", "doing", "view", "analyse", "analyze", "check", "read", "direction", "buy or sell", "safe to enter", "can i enter", "should i enter", "good trade", "trade now"]):
            if _has_any(t, ["story", "full story", "market story"]):
                return [f"market story {sym}"]
            if _has_any(t, ["plan", "scenario", "what should we do"]):
                return [f"scenario {sym}"]
            if _has_any(t, ["safe to enter", "can i enter", "should i enter", "trade now", "good trade"]):
                return [f"check {sym}", "why wait"]
            return [f"check {sym}"]
        if _has_any(t, ["story", "full story", "market story"]):
            return [f"market story {sym}"]
        if _has_any(t, ["plan", "scenario", "plan a", "plan b", "plan c"]):
            return [f"scenario {sym}"]
        if _has_any(t, ["invalid", "invalidation", "wrong if", "when wrong", "wrong", "idea wrong", "cancel idea"]):
            return [f"trade invalidation {sym}"]
        if _has_any(t, ["protect", "lock profit", "secure", "breakeven", "break even", "move sl"]):
            return [f"breakeven {sym}"]
        if _has_any(t, ["trail", "trailing"]):
            return [f"trail {sym}"]
        if _has_any(t, ["close half", "partial close", "book half"]):
            return [f"close half {sym}"]
        if _has_any(t, ["close", "exit trade"]):
            return [f"close {sym}"]
        if _has_any(t, ["lot", "position size", "size"]):
            return [f"mt5 lot {sym}"]
        if _has_any(t, ["order doctor", "why not punching", "not executing", "execution problem", "punch problem"]):
            return [f"order doctor {sym}"]
        if _has_any(t, ["neural", "nn", "deep brain"]):
            return [f"neural predict {sym}"]

    # Non-symbol natural requests.
    if _has_any(t, ["best trade", "strongest trade", "where is best setup", "best setup", "which pair is best", "find best"]):
        return ["strongest"]
    if _has_any(t, ["scan all", "scan market", "scan pairs", "check all pairs", "look at all pairs"]):
        return ["scanner"]
    if _has_any(t, ["open trades", "running trades", "my trades", "active positions", "current positions"]):
        return ["open positions"]
    if _has_any(t, ["profit", "loss", "pnl", "p l"]):
        return ["open positions"]
    if _has_any(t, ["balance", "equity", "account info", "my account"]):
        return ["mt5 account"]
    if _has_any(t, ["connect broker", "connect my broker", "connect mt5", "login mt5"]):
        return ["connect mt5"] if "mt5" in t else ["connect broker"]
    if _has_any(t, ["learn from history", "learn my trades", "learn closed trades"]):
        return ["mt5 learn history 30d"]
    if _has_any(t, ["train your brain", "train brain", "train model"]):
        return ["ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv"]
    if _has_any(t, ["news risk", "today news", "macro risk", "market news"]):
        return ["news report"]
    if _has_any(t, ["why wait", "avoid trade", "why avoid", "should we take this trade"]):
        return ["why wait"]
    if _has_any(t, ["think like trader", "think like a trader", "human trader", "human brain"]):
        return ["human brain"]
    if _has_any(t, ["simple commands", "what can i type", "what can i say", "commands list"]):
        return ["simple help"]
    return []
