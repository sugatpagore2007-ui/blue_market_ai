"""Phase 15.21 Natural Intent Brain.

This layer lets Blue understand normal English/Hinglish-style text without the
user memorising coded commands. It returns the SAME safe internal commands that
already exist in Blue, so the old command system remains intact.

Safety rule: this resolver never creates direct buy/sell execution commands.
Trade execution still goes through autopilot, risk filters, MT5 checks and the
Order Punch Shield.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Canonical English symbols Blue supports in normal user text.
SYMBOL_ALIASES = {
    "gold": "gold", "xau": "gold", "xauusd": "gold", "xau usd": "gold", "xau/usd": "gold",
    "btc": "btc", "bitcoin": "btc", "btcusd": "btc", "btc usd": "btc", "btc/usd": "btc",
    "eth": "eth", "ethereum": "eth", "ethusd": "eth", "eth usd": "eth", "eth/usd": "eth",
    "eur": "eurusd", "euro": "eurusd", "eurusd": "eurusd", "eur usd": "eurusd", "eur/usd": "eurusd",
    "gbp": "gbpusd", "pound": "gbpusd", "gbpusd": "gbpusd", "gbp usd": "gbpusd", "gbp/usd": "gbpusd",
    "jpy": "usdjpy", "yen": "usdjpy", "usdjpy": "usdjpy", "usd jpy": "usdjpy", "usd/jpy": "usdjpy",
    "silver": "silver", "xag": "silver", "xag usd": "silver", "xagusd": "silver",
    "oil": "usoil", "us oil": "usoil", "crude": "usoil", "wti": "usoil",
    "ustec": "ustec", "us tech": "ustec", "us tech 100": "ustec", "nasdaq": "nasdaq", "nas100": "nasdaq", "us100": "nasdaq",
    "spx": "spx", "sp500": "spx", "s&p 500": "spx", "us500": "spx",
    "dxy": "dxy", "dollar index": "dxy",
}

DANGEROUS_EXECUTION_WORDS = {
    "execute", "place order", "open order", "buy now", "sell now", "market buy", "market sell",
    "real account", "live account", "increase risk", "double lot", "all in",
}


def _clean(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("?", " ").replace("!", " ").replace(",", " ")
    t = re.sub(r"\s+", " ", t)
    return t


def extract_symbols_natural(text: str) -> List[str]:
    t = " " + _clean(text) + " "
    found: List[str] = []
    # Longer aliases first to avoid xau matching before xau usd.
    for alias, canonical in sorted(SYMBOL_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        if re.search(pattern, t) and canonical not in found:
            found.append(canonical)
    return found


def _has_any(t: str, words: List[str]) -> bool:
    return any(w in t for w in words)


def _symbol_or_gold(text: str) -> str:
    syms = extract_symbols_natural(text)
    return syms[0] if syms else "gold"


def _multi_symbol_or_default(text: str) -> List[str]:
    return extract_symbols_natural(text) or ["gold"]


def resolve_natural_intent(text: str) -> Tuple[List[str], str, int]:
    """Return (commands, intent_name, confidence).

    Commands are safe internal English commands already handled by Blue.
    Empty commands means the normal parser should continue.
    """
    t = _clean(text)
    if not t:
        return [], "empty", 0

    # Safety: direct execution phrases should not be guessed by natural intent.
    direct_market_order = (
        any(w in t for w in DANGEROUS_EXECUTION_WORDS)
        or bool(re.search(r"\b(buy|sell)\b.*\bnow\b", t))
        or bool(re.search(r"\bnow\b.*\b(buy|sell)\b", t))
    )
    if direct_market_order:
        if "autopilot" in t:
            return ["blue autopilot on"], "safe_autopilot_start", 75
        return ["order doctor " + _symbol_or_gold(t)], "execution_safety_check", 72

    # Emergency / stop intent.
    if _has_any(t, ["stop everything", "stop all", "pause everything", "turn off everything", "shut down automation", "stop blue"]):
        return ["stop everything"], "stop_everything", 98
    if t in {"stop", "pause", "halt"}:
        return ["stop everything"], "stop_everything", 88
    if t in {"exit", "quit", "close blue", "close app"}:
        return ["exit"], "exit", 96

    # Help/menu intent.
    if _has_any(t, ["what can i say", "show commands", "show english commands", "english commands", "simple commands", "command list", "help me"]):
        return ["simple help"], "help", 95

    # Voice/text mode.
    if _has_any(t, ["start voice", "voice mode", "listen to me", "start listening", "talk mode", "voice and text", "parallel mode", "dual mode"]):
        return ["voice"], "voice_on", 90
    if _has_any(t, ["stop listening", "voice off", "turn off voice", "disable voice"]):
        return ["voice off"], "voice_off", 90
    if _has_any(t, ["quiet", "stop speaking", "be quiet", "silence"]):
        return ["stop speaking"], "quiet", 90

    # Autopilot/automatic system.
    if _has_any(t, ["turn autopilot on", "start autopilot", "autopilot start", "auto trading on", "automatic trading on"]):
        return ["blue autopilot on"], "autopilot_on", 93
    if _has_any(t, ["turn autopilot off", "stop autopilot", "autopilot stop", "auto trading off"]):
        return ["blue autopilot off"], "autopilot_off", 93
    if _has_any(t, ["autopilot status", "auto trading status", "is autopilot running"]):
        return ["blue autopilot status"], "autopilot_status", 90
    if _has_any(t, ["full auto on", "start full auto", "everything automatic", "automatic mode on"]):
        return ["full auto on"], "full_auto_on", 91
    if _has_any(t, ["full auto off", "automatic mode off", "disable automatic"]):
        return ["full auto off"], "full_auto_off", 91

    # Open positions / performance.
    if _has_any(t, ["open trades", "open positions", "show trades", "current trades", "my trades", "running trades", "current profit", "profit loss", "pnl"]):
        return ["open positions"], "open_positions", 92
    if _has_any(t, ["win rate", "winrate", "performance", "stats", "statistics", "results"]):
        syms = extract_symbols_natural(t)
        if syms:
            return [f"win rate {syms[0]}"], "symbol_win_rate", 90
        return ["win rate"], "win_rate", 88
    if _has_any(t, ["journal", "trade journal", "trade history report"]):
        return ["journal"], "journal", 85

    # Account and broker.
    if _has_any(t, ["connect mt5", "connect terminal", "connect my mt5"]):
        return ["connect mt5"], "connect_mt5", 94
    if _has_any(t, ["connect broker", "connect my broker", "broker connect"]):
        return ["connect broker"], "connect_broker", 90
    if _has_any(t, ["broker status", "which broker", "show broker"]):
        return ["broker status"], "broker_status", 90
    if _has_any(t, ["use exness", "exness broker"]):
        return ["broker set exness"], "broker_profile", 94
    if _has_any(t, ["use xm", "xm broker"]):
        return ["broker set xm"], "broker_profile", 94
    if _has_any(t, ["auto broker", "detect broker"]):
        return ["broker set auto"], "broker_profile", 91
    if _has_any(t, ["account", "balance", "equity", "margin"]):
        return ["mt5 account"], "account", 84
    if _has_any(t, ["risk setting", "set risk", "save risk", "risk percent"]):
        return ["set risk"], "risk", 86

    # Learning.
    if _has_any(t, ["train your brain", "train blue", "train model", "train ml", "train dataset"]):
        return ["ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv"], "train_ml", 88
    if _has_any(t, ["train neural", "neural train", "deep learn", "train neural network"]):
        return ["neural train"], "train_neural", 92
    if _has_any(t, ["learn from mt5", "mt5 history", "closed trades", "learn account history"]):
        return ["mt5 learn history 30d"], "mt5_learn", 90
    if _has_any(t, ["learn from history", "learn journal", "learn from journal", "learn demo trades"]):
        return ["journal learn history"], "journal_learn", 88
    if _has_any(t, ["internet learn", "learn from internet", "environment learn", "learn market environment"]):
        return ["internet learn"], "internet_learn", 90
    if _has_any(t, ["learning status", "learn status", "background learning status"]):
        return ["background learn status"], "learning_status", 87
    if t in {"learn", "learn now", "start learning"}:
        return ["background learn now"], "learn_now", 82

    # Trade management. These are management actions but still routed to existing MT5 safe handlers.
    if _has_any(t, ["make", "move", "protect", "safe", "secure", "lock profit", "breakeven", "break even"]):
        syms = extract_symbols_natural(t)
        if syms and _has_any(t, ["breakeven", "break even", "entry", "safe", "protect", "secure"]):
            return [f"breakeven {syms[0]}"], "breakeven", 88
    if _has_any(t, ["trail", "trailing"]):
        syms = extract_symbols_natural(t)
        if syms:
            return [f"trail {syms[0]}"], "trail", 88
    if _has_any(t, ["close half", "partial close", "book half"]):
        syms = extract_symbols_natural(t)
        if syms:
            return [f"close half {syms[0]}"], "partial_close", 86
    if _has_any(t, ["close trade", "close position", "close my"]):
        syms = extract_symbols_natural(t)
        if syms:
            return [f"close {syms[0]}"], "close_symbol", 83
    if _has_any(t, ["manager on", "start manager", "auto manager on"]):
        return ["manager on"], "manager_on", 90
    if _has_any(t, ["manager off", "stop manager", "auto manager off"]):
        return ["manager off"], "manager_off", 90
    if _has_any(t, ["manager status", "trade manager"]):
        return ["manager"], "manager_status", 85

    # Human trader/natural output.
    if _has_any(t, ["full story", "market story", "story of", "tell me story", "explain market"]) or ("story" in t and _has_any(t, ["explain", "full", "tell", "market"])):
        return [f"market story {_symbol_or_gold(t)}"], "market_story", 94
    if _has_any(t, ["plan", "scenario", "what should we do", "entry plan", "trade plan", "plan a", "plan b"]):
        return [f"scenario {_symbol_or_gold(t)}"], "scenario", 91
    if _has_any(t, ["invalidation", "invalid", "wrong if", "where is wrong", "cancel idea"]):
        return [f"trade invalidation {_symbol_or_gold(t)}"], "invalidation", 90
    if _has_any(t, ["why wait", "why are we waiting", "why avoid", "avoid this trade", "should we take this trade"]):
        return ["why wait"], "why_wait", 88
    if _has_any(t, ["think like trader", "human brain", "human trader", "natural trader"]):
        return ["human brain"], "human_brain", 87
    if _has_any(t, ["safe trader", "conservative mode", "safe mode"]):
        return ["safe trader mode"], "safe_mode", 88
    if _has_any(t, ["aggressive trader", "aggressive mode"]):
        return ["aggressive trader mode"], "aggressive_mode", 88

    # Market analysis intent. This is the most common use.
    syms = _multi_symbol_or_default(t)
    if syms and _has_any(t, [
        "buy or sell", "buy sell", "direction", "what about", "tell me", "check", "analyze", "analyse",
        "signal", "setup", "entry", "view", "opinion", "market read", "read", "kya", "scene", "trade",
        "should i buy", "should i sell", "can i enter", "good trade", "forecast", "prediction"
    ]):
        # If user asks for a symbol with no detailed keyword, analyze it.
        if len(syms) > 1:
            return [f"check {s}" for s in syms], "multi_analysis", 87
        return [f"check {syms[0]}"], "analysis", 86

    # Strongest/scan intent.
    if _has_any(t, ["best trade", "strongest setup", "strongest trade", "top setup", "best setup"]):
        return ["strongest"], "strongest", 91
    if _has_any(t, ["scan market", "scan pairs", "scan all", "all pairs", "market scan"]):
        return ["scanner"], "scanner", 89

    # Symbol alone: analyze it.
    syms_only = extract_symbols_natural(t)
    if syms_only and len(t.split()) <= 4:
        return [f"check {syms_only[0]}"], "symbol_analysis", 82

    return [], "unknown", 0
