"""Natural language command parser for Blue Market AI.
Turns friendly phrases and multiple requests into safe internal commands.
"""
from __future__ import annotations

import re
from typing import List

from config import SYMBOLS, DEFAULT_TRADE_STYLE
from utils.trade_style import detect_trade_style
from utils.natural_intent_router import infer_intent_commands

# Longer names first so "xau/usd" is found before "xau".
SYMBOL_WORDS = sorted(SYMBOLS.keys(), key=len, reverse=True)

ALIASES = {
    "xau usd": "gold",
    "xauusd": "gold",
    "xau/usd": "gold",
    "gold": "gold",
    "xau": "gold",
    "eur": "eurusd",
    "euro": "eurusd",
    "euro dollar": "eurusd",
    "eu": "eurusd",
    "gbp": "gbpusd",
    "pound": "gbpusd",
    "cable": "gbpusd",
    "gu": "gbpusd",
    "jpy": "usdjpy",
    "yen": "usdjpy",
    "uj": "usdjpy",
    "usd jpy": "usdjpy",
    "usdjpy": "usdjpy",
    "bitcoin": "btc",
    "btcusd": "btc",
    "btc/usd": "btc",
    "btc": "btc",
    "ethereum": "eth",
    "ethusd": "eth",
    "eth/usd": "eth",
    "eth": "eth",
    "silver": "silver",
    "xag": "silver",
    "xag usd": "silver",
    "xagusd": "silver",
    "dxy": "dxy",
    "dollar index": "dxy",
    "crude oil": "usoil",
    "us oil": "usoil",
    "wti": "usoil",
    "oil": "usoil",
    "ustec": "ustec",
    "us tech": "ustec",
    "us tech 100": "ustec",
    "nas100": "nasdaq",
    "us100": "nasdaq",
    "nq": "nasdaq",
    "nasdaq": "nasdaq",
    "sp500": "spx",
    "s&p500": "spx",
    "s&p 500": "spx",
    "us500": "spx",
    "spx": "spx",
}

STOP_WORDS = {"please", "can", "you", "me", "the", "a", "an", "for", "of", "on", "now", "market", "pair", "chart", "setup"}

# Phase 15.4 friendly command layer.
# These short words are translated into the older internal commands so users can
# speak/type naturally without memorising long syntax.
READY_ML_DATASET = "datasets/blue_ml_ready_combined_1050_rows.csv"

QUICK_ALIASES = {
    # help / menu
    "help": "simple help",
    "?": "simple help",
    "menu": "simple help",
    "commands": "simple help",
    "command": "simple help",
    "simple commands": "simple help",
    "short commands": "simple help",
    "what can i say": "simple help",
    "what should i type": "simple help",
    "show simple commands": "simple help",
    "show commands": "simple help",
    "list commands": "simple help",
    "help show simple commands": "simple help",

    # startup / stop / status
    "start": "blue start status",
    "run": "blue start status",
    "status": "status",
    "full status": "status",
    "show status": "status",
    "full blue system status": "status",
    "blue system status": "status",
    "stop": "stop everything",
    "stop all": "stop everything",
    "stop everything": "stop everything",
    "exit": "exit",
    "quit": "exit",
    "bye": "exit",
    "close blue": "exit",
    "close app": "exit",
    "blue doctor": "blue doctor",
    "doctor": "blue doctor",
    "self doctor": "blue doctor",
    "health": "blue doctor",
    "health check": "blue doctor",
    "system check": "blue doctor",
    "self heal on": "self heal on",
    "self healing on": "self heal on",
    "doctor on": "self heal on",
    "self heal off": "self heal off",
    "self healing off": "self heal off",
    "doctor off": "self heal off",

    # common trading actions
    "best": "strongest",
    "top": "strongest",
    "top trade": "strongest",
    "best trade": "strongest",
    "show best trade": "strongest",
    "show me best trade": "strongest",
    "show my best trade": "strongest",
    "tell me best trade": "strongest",
    "scan": "scanner",
    "scan auto": "autonomous all pairs",
    "market": "scanner",
    "all market": "scanner",
    "all pairs": "scanner",
    "why": "why last trade",
    "reason": "why last trade",
    "news": "news report",
    "macro": "macro report",

    # journal / stats / open trades
    "trades": "open positions",
    "open trades": "open positions",
    "show trades": "open positions",
    "show my open trades": "open positions",
    "show me open trades": "open positions",
    "my open trades": "open positions",
    "profit": "open positions",
    "pnl": "open positions",
    "journal": "journal",
    "history": "journal",
    "stats": "win rate",
    "statistics": "win rate",
    "performance": "win rate",
    "show everything": "win rate",
    "show me everything": "win rate",
    "winrate": "win rate",
    "win rate": "win rate",
    "show win rate": "win rate",
    "show my win rate": "win rate",
    "account win rate": "connected account win rate",
    "connected account win rate": "connected account win rate",

    # account / broker
    "balance": "mt5 account",
    "account": "mt5 account",
    "risk": "set risk",
    "set risk": "set risk",
    "broker": "broker status",
    "broker status": "broker status",
    "connect": "connect broker",
    "login": "connect broker",
    "connect broker": "connect broker",
    "connect mt5": "connect mt5",
    "use auto broker": "broker set auto",
    "auto broker": "broker set auto",

    # autopilot / safety
    "go": "blue autopilot on",
    "auto on": "blue autopilot on",
    "autopilot on": "blue autopilot on",
    "autopilot off": "blue autopilot off",
    "pause": "blue autopilot off",
    "resume": "blue autopilot on",
    "autopilot": "blue autopilot status",
    "auto": "blue autopilot status",
    "safe": "auto status",
    "safety": "auto status",

    # learning / ML
    "learn": "background learn now",
    "learn now": "background learn now",
    "learn on": "background learn start",
    "auto learn on": "background learn start",
    "learn off": "background learn stop",
    "auto learn off": "background learn stop",
    "learn status": "background learn status",
    "learning status": "background learn status",
    "learn from history": "journal learn history",
    "history learn": "journal learn history",
    "learn from blue journal": "journal learn history",
    "learn from demo trades": "journal learn history",
    "train": f"ml train dataset {READY_ML_DATASET}",
    "train brain": f"ml train dataset {READY_ML_DATASET}",
    "train your brain": f"ml train dataset {READY_ML_DATASET}",
    "train ready": f"ml train dataset {READY_ML_DATASET}",
    "train data": f"ml train dataset {READY_ML_DATASET}",
    "train dataset": f"ml train dataset {READY_ML_DATASET}",
    "brain": "ml dataset report",
    "ml report": "ml dataset report",
    "model": "ml dataset report",
    "model report": "ml dataset report",
    "data report": "ml dataset report",
    "dataset report": "ml dataset report",
    "template": "ml dataset template",
    "ml help": "ml dataset help",
    "data help": "ml dataset help",
    "retrain": "retrain now",
    "retrain now": "retrain now",
    "memory": "trade memory",
    "trade memory": "trade memory",
    "mt5 learn": "mt5 learn history 30d",
    "learn mt5": "mt5 learn history 30d",
    "learn history": "mt5 learn history 30d",
    "journal learn": "journal learn history",
    "learn journal": "journal learn history",
    "backtest": "backtest learn all",
    "backtest learn": "backtest learn all",
    "learn backtest": "backtest learn all",
    "backtest all": "backtest learn all",
    "backtest everything": "backtest learn all",
    "backtest all trades": "backtest learn all",
    "backtest all the trades": "backtest learn all",
    "backtest all data": "backtest learn all",
    "internet": "internet report",
    "web": "internet report",
    "environment": "internet report",
    "internet help": "internet help",
    "web help": "internet help",
    "environment help": "internet help",
    "internet seed": "internet seed",
    "web seed": "internet seed",
    "internet sources": "internet sources",
    "web sources": "internet sources",
    "internet learn": "internet learn",
    "web learn": "internet learn",
    "learn from internet": "internet learn",
    "environment learn": "internet learn",
    "environment study": "internet learn",
    "internet report": "internet report",
    "web report": "internet report",
    "internet memory": "internet report",
    "internet on": "internet on",
    "web on": "internet on",
    "environment on": "internet on",
    "internet off": "internet off",
    "web off": "internet off",
    "environment off": "internet off",
    "baby brain": "baby brain",
    "newborn brain": "baby brain",
    "human learning brain": "baby brain",
    "self learn": "self learn",
    "self learning": "self learn",
    "self learn on": "self learn on",
    "self learn off": "self learn off",
    "self report": "self report",
    "profitability report": "profitability report",
    "profitability flywheel": "profitability flywheel",
    "mistake report": "mistake report",
    "loss report": "mistake report",
    "calibrate confidence": "calibrate confidence",
    "session quota": "session quota",
    "trade quota": "session quota",
    "daily quota": "session quota",
    "neural": "neural report",
    "nn": "neural report",
    "neural help": "neural help",
    "nn help": "neural help",
    "neural train": "neural train",
    "nn train": "neural train",
    "train neural": "neural train",
    "train neural network": "neural train",
    "neural report": "neural report",
    "nn report": "neural report",
    "neural status": "neural report",
    "nn status": "neural report",
    "neural on": "neural on",
    "nn on": "neural on",
    "neural off": "neural off",
    "nn off": "neural off",
    "neural background on": "neural background on",
    "nn background on": "neural background on",
    "neural background off": "neural background off",
    "nn background off": "neural background off",
    "deep learn": "neural train",
    "human brain": "human brain",
    "human report": "human report",
    "cognitive status": "cognitive status",
    "world model": "world model",
    "market dna": "market dna",
    "brain status": "brain status",
    "cognitive now": "cognitive now",
    "cme": "cme status",
    "cme status": "cme status",
    "cme report": "cme status",
    "cme brain": "cme status",
    "cme refresh": "cme refresh",
    "cme learn": "cme refresh",
    "cme update": "cme refresh",
    "institutional data": "cme status",
    "think like a trader": "human brain",
    "trader mode": "trader modes",
    "safe trader mode": "safe trader mode",
    "aggressive trader mode": "aggressive trader mode",
    "market story": "market story gold",
    "full market story": "market story gold",
    "scenario": "scenario gold",
    "plan": "plan gold",
    "why wait": "why wait",
    "should we take this trade": "should we take this trade",
    "trade invalidation": "trade invalidation gold",

    # mode/personality
    "trader modes": "trader modes",
    "modes": "trader modes",
    "mode": "trader modes",
    "conservative": "trader mode conservative",
    "safe mode": "trader mode conservative",
    "balanced": "trader mode balanced",
    "normal": "trader mode balanced",
    "aggressive": "trader mode aggressive",
    "fast": "trader mode aggressive",
    "learning mode": "trader mode learning",
    "practice": "trader mode learning",
    "demo mode": "trader mode learning",

    # candles / strategy knowledge
    "patterns": "candlestick patterns",
    "candle patterns": "candlestick patterns",
    "candles": "candlestick patterns",
    "candle help": "candle help",
    "bb": "booming bulls report",
    "booming": "booming bulls report",
    "booming bulls": "booming bulls report",

    # trade management / voice / UI
    "manager on": "auto manager on",
    "manager off": "auto manager off",
    "manage": "auto manager on",
    "manager": "auto manager status",
    "pyramid": "pyramiding status",
    "voice": "voice on",
    "talk": "voice on",
    "voice text on": "voice on",
    "text voice on": "voice on",
    "voice and text": "voice on",
    "dual mode": "voice on",
    "parallel mode": "voice on",
    "both mode": "voice on",
    "voice text status": "voice background status",
    "parallel voice status": "voice background status",
    "voice text off": "voice off",
    "text voice off": "voice off",
    "quiet": "stop speaking",

    "voice on": "voice on",
    "start voice": "voice on",
    "start listening": "voice on",
    "listening on": "voice on",
    "microphone on": "voice on",
    "voice off": "voice off",
    "stop voice": "voice off",
    "stop listening": "voice off",
    "listening off": "voice off",
    "microphone off": "voice off",
    "voice background status": "voice background status",
    "background voice status": "voice background status",
    "voice listener status": "voice background status",
    "listening status": "voice background status",
    "voice session": "voice session",

    "voice status": "voice status",
    "mic status": "voice status",
    "microphone status": "voice status",
    "voice install help": "voice install help",
    "mic install help": "voice install help",
    "install voice": "voice install help",
    "screenshot": "screenshot",
    "ocr": "live chart ocr",
    "orb": "orb",
}

def clean_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.replace("&", " and ")
    text = text.replace("/", "/")
    text = re.sub(r"[|]+", " and ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def split_user_commands(text: str) -> List[str]:
    """Split one user line into separate command phrases.
    Examples: 'scan market and check gold', 'check gold then stats'.
    """
    text = clean_text(text)
    # Keep phrases like "risk and reward" less relevant here; this command shell is simple.
    parts = re.split(r"\s*(?:,|;|\bthen\b|\band also\b|\balso\b|\bafter that\b|\band\b)\s*", text)
    return [p.strip() for p in parts if p and p.strip()]


def extract_symbols(text: str) -> List[str]:
    text = clean_text(text)
    found: List[str] = []

    # phrase aliases first
    for phrase, canonical in ALIASES.items():
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
            if canonical not in found:
                found.append(canonical)

    # configured keys
    for sym in SYMBOL_WORDS:
        normalized = sym.replace("/", " ")
        patterns = {sym, normalized}
        for pat in patterns:
            if re.search(rf"(?<!\w){re.escape(pat)}(?!\w)", text):
                canonical = ALIASES.get(sym, sym)
                if canonical not in found:
                    found.append(canonical)
    return found


def _path_from_text(text: str, keywords: List[str]) -> str:
    out = text
    for k in keywords:
        out = out.replace(k, " ")
    return out.strip().strip('"').strip("'")


def normalize_single_command(text: str) -> List[str]:
    """Return one or more canonical commands for a phrase."""
    t = clean_text(text)
    if not t:
        return []
    # Phase 15.6 wake-word cleanup for text and voice.
    for wake in ["hey blue", "ok blue", "okay blue", "hello blue", "hi blue", "blue", "hey google", "ok google", "okay google", "hey siri", "alexa"]:
        if t == wake:
            return ["simple help"]
        if t.startswith(wake + " "):
            t = t[len(wake):].strip()
            break

    # Help/status phrases that are longer than one exact alias.
    if t.startswith("help") or "simple commands" in t or "show commands" in t or "list commands" in t:
        return ["simple help"]
    if "system status" in t or "full status" in t or t in {"status", "show status"}:
        return ["status"]

    # Short/friendly exact aliases first.
    if t in QUICK_ALIASES:
        return [QUICK_ALIASES[t]]
    if any(x in t for x in ["learn to be profitable", "increase probability", "profitability memory", "self learning report"]):
        return ["profitability report"]
    if any(x in t for x in ["how many trades today", "trade limit", "london session limit", "new york session limit", "ny session limit"]):
        return ["session quota"]
    if any(x in t for x in ["what mistakes", "show mistakes", "bad setups", "weak setups"]):
        return ["mistake report"]

    # Human phrase: "backtest all the trades from csv, journal, demo trade, ML".
    if "backtest" in t and any(x in t for x in ["all", "csv", "cvs", "journal", "demo", "ml", "everything"]):
        return ["backtest learn all"]

    # Friendly patterns with a path/number/symbol argument.
    # Examples: "train mydata.csv", "learn 90d", "gold candles".
    internet_add_match = re.match(r"^(?:internet add|web add|environment add)\s+(https?://\S+)$", t)
    if internet_add_match:
        return ["internet add " + internet_add_match.group(1).strip()]

    train_match = re.match(r"^(?:train|train data|train dataset|train my data)\s+(.+\.csv)$", t)
    if train_match:
        return ["ml train dataset " + train_match.group(1).strip().strip('\"')]

    neural_train_match = re.match(r"^(?:neural train dataset|nn train dataset|train neural dataset)\s+(.+\.csv)$", t)
    if neural_train_match:
        return ["neural train dataset " + neural_train_match.group(1).strip().strip('\"')]


    # Broker profile switching: "use exness", "use xm broker", "switch to icmarkets".
    broker_match = re.match(r"^(?:use|switch to|set broker|broker)\s+(exness|xm|auto|auto broker|icmarkets|ic markets|pepperstone|octa|fbs|hfm|generic_mt5|generic mt5|ctrader)(?:\s+broker)?$", t)
    if broker_match:
        profile = broker_match.group(1).replace(" ", "_")
        if profile == "auto_broker":
            profile = "auto"
        if profile == "ic_markets":
            profile = "icmarkets"
        if profile == "generic_mt5":
            profile = "generic_mt5"
        return ["broker set " + profile]

    if "connect" in t and "broker" in t:
        return ["connect broker"]
    if "connect" in t and "mt5" in t:
        return ["connect mt5"]
    if any(x in t for x in ["any problem", "code problem", "runtime problem", "system problem", "check problem", "fix problem", "self heal", "heal blue"]):
        return ["blue doctor"]
    if "show my open trades" in t or "show open trades" in t or "show me open trades" in t:
        return ["open positions"]
    if "why should we take this trade" in t:
        return ["why last trade"]
    if t.startswith("news") or "news risk" in t:
        return ["news report"]
    if t.startswith("macro") or "macro context" in t:
        return ["macro report"]

    if "tell me the full" in t and "story" in t:
        syms = extract_symbols(t)
        return [f"market story {syms[0]}"] if syms else ["market story gold"]
    if "market story" in t or ("full" in t and "story" in t):
        syms = extract_symbols(t)
        return [f"market story {syms[0]}"] if syms else ["market story gold"]
    if t.startswith("scenario") or t.startswith("plan") or "what is the plan" in t or "trading plan" in t:
        syms = extract_symbols(t)
        base = "scenario" if not t.startswith("plan") else "plan"
        return [f"{base} {syms[0]}"] if syms else [f"{base} gold"]
    if "invalidation" in t:
        syms = extract_symbols(t)
        return [f"trade invalidation {syms[0]}"] if syms else ["trade invalidation gold"]
    if t == "why wait" or "why should we avoid this trade" in t or "should we take this trade" in t:
        return ["why wait"]

    # Win-rate commands can apply to the connected account overall or to any symbol.
    if any(x in t for x in ["win rate", "winrate", "take out win rate", "performance", "stats", "statistics"]):
        syms_for_winrate = extract_symbols(t)
        day_match = re.search(r"(\d+)\s*(?:d|day|days)", t)
        day_suffix = (" " + day_match.group(0).replace(" ", "")) if day_match else ""
        if syms_for_winrate:
            return [f"win rate {s}{day_suffix}" for s in syms_for_winrate]
        if any(x in t for x in ["connected account", "account", "everything", "all"]):
            return ["connected account win rate" + day_suffix]
        return ["win rate" + day_suffix]

    neural_predict_symbols = extract_symbols(t)
    if neural_predict_symbols and (t.startswith("neural predict") or t.startswith("nn predict") or t.startswith("neural ") or t.startswith("nn ")):
        return [f"neural predict {s}" for s in neural_predict_symbols]

    # Symbol-specific broker/account helpers for all supported pairs, not only gold.
    syms_for_helpers = extract_symbols(t)
    if syms_for_helpers:
        if t.startswith("symbols ") or t.startswith("symbol ") or "show symbols" in t:
            return [f"show mt5 symbols {s}" for s in syms_for_helpers]
        if t.startswith("spec ") or t.startswith("symbol spec ") or "specification" in t:
            return [f"symbol spec {s}" for s in syms_for_helpers]
        if t.startswith("lot ") or "lot size" in t:
            return [f"mt5 lot {s}" for s in syms_for_helpers]
        if t.startswith("reason ") or "reason" in t or "basis" in t:
            return [f"check {s}" for s in syms_for_helpers]
        if t.startswith("close half") or t.startswith("half close") or "close half" in t:
            return [f"close half {s}" for s in syms_for_helpers]
        if t.startswith("close "):
            return [f"close {s}" for s in syms_for_helpers]
        if t.startswith("trail ") or "trailing" in t:
            return [f"trail {s}" for s in syms_for_helpers]
        if t.startswith("be ") or "breakeven" in t or "break even" in t or "move" in t and "breakeven" in t:
            return [f"breakeven {s}" for s in syms_for_helpers]

    learn_days = re.match(r"^(?:learn|mt5 learn|learn mt5|learn history)\s+(all|\d+\s*d?|\d+\s*days?)(?:\s+(1m|3m|5m|15m|30m|1h|4h|1d|daily))?$", t)
    if learn_days:
        day_token = learn_days.group(1).replace(" ", "")
        tf_token = (learn_days.group(2) or "").strip()
        return ["mt5 learn history " + day_token + ((" " + tf_token) if tf_token else "")]

    syms_for_candles = extract_symbols(t)
    if syms_for_candles and any(w in t for w in ["candle", "candles", "pattern", "patterns"]):
        # Keep timeframe if user says e.g. "gold candles 15m".
        tf = ""
        for token in ["1m","3m","5m","15m","30m","1h","4h","1d","daily"]:
            if re.search(rf"(?<!\w){token}(?!\w)", t):
                tf = " " + token
                break
        return [f"candles {s}{tf}" for s in syms_for_candles]

    # direct exits / controls
    if t in {"exit", "quit", "close", "stop app"}:
        return ["exit"]
    if t in {"voice", "voice mode", "start voice", "start listening", "continuous listening"}:
        return ["voice"]
    if any(x in t for x in ["stop speaking", "interrupt", "silence", "be quiet", "shut up"]):
        return ["stop speaking"]
    if any(x in t for x in ["floating orb", "open orb", "show orb", "jarvis orb"]):
        return ["orb"]

    # Phase 10+ direct commands should not be collapsed into generic memory/account/backtest commands.
    direct_phase_commands = {
        "phase10 status", "human brain status", "trader brain status", "trader modes", "personality modes",
        "internet help", "internet seed", "internet sources", "internet learn", "internet report", "internet on", "internet off", "baby brain",
        "neural help", "neural train", "neural report", "neural on", "neural off", "neural background on", "neural background off",
        "human brain", "human report", "safe trader mode", "aggressive trader mode", "why wait", "should we take this trade",
        "cognitive status", "cognitive report", "world model", "market dna", "brain status", "cognitive now", "brain now", "world model now", "cognitive on", "cognitive off",
        "cme status", "cme report", "cme brain", "cme refresh", "cme learn", "cme update", "cme on", "cme off", "institutional data",
        "blue doctor", "doctor", "self doctor", "health", "health check", "system check", "self heal on", "self heal off",
        "self learn", "self learn on", "self learn off", "self report", "profitability report", "mistake report", "calibrate confidence", "session quota",
        "trade memory", "memory report", "learning memory", "broker intelligence", "broker brain", "symbol intelligence",
        "phase15 status", "auto history status", "history learning status", "learning report", "phase15 report",
        "auto history report", "auto learn on", "auto learning on", "auto learn off", "auto learning off",
        "auto retrain on", "auto ml retrain on", "auto retrain off", "auto ml retrain off",
        "retrain now", "ml retrain now", "train from imported history", "journal learn history",
        "learn blue journal", "blue journal learn", "learn demo journal", "mt5 learn help",
        "mt5 history learning help", "history learning help", "backtest learning help", "backtest import help",
        "backtest template", "create backtest template",
    }
    if t in direct_phase_commands:
        return [t]
    if (t.startswith("trader mode ") or t.startswith("set trader mode ") or
        t.startswith("internet add ") or t.startswith("web add ") or t.startswith("environment add ") or
        t.startswith("mt5 learn history") or t.startswith("learn mt5 history") or
        t.startswith("backtest learn") or t.startswith("backtest import ")):
        return [t]

    # journal / stats words
    if any(x in t for x in ["open trades", "show trades", "show me trades", "show me open trades"]):
        return ["open positions"]
    if any(x in t for x in ["journal", "trade history"]):
        return ["journal"]
    if any(x in t for x in ["close trade", "update trade", "mark trade", "trade result"]):
        return ["close trade"]
    if any(x in t for x in ["win rate", "winrate", "performance", "stats", "statistics", "result report", "take out win rate"]):
        return ["win rate"]
    if any(x in t for x in ["account", "balance", "risk setting", "risk setup"]):
        return ["account"]
    if any(x in t for x in ["risk test", "monte carlo", "risk simulation"]):
        return ["risk-test"]

    # scanner / strongest
    if any(x in t for x in ["strongest", "best setup", "top setup", "best trade"]):
        return ["strongest"]
    if any(x in t for x in ["scan market", "market scanner", "scanner", "scan all"]):
        return ["scanner"]

    # screenshot / chart detection
    if any(x in t for x in ["live chart ocr", "ocr help"]):
        return ["live chart ocr"]
    if t.startswith("detect chart") or any(x in t for x in ["visual detect", "detect candle", "detect my chart"]):
        path = _path_from_text(t, ["detect chart", "visual detect", "detect candle", "detect my chart"])
        return ["detect chart " + path if path else "detect chart"]
    if t.startswith("screenshot") or t.startswith("image") or any(x in t for x in ["analyze screenshot", "analyse screenshot", "analyze image", "analyse image"]):
        path = _path_from_text(t, ["screenshot", "image", "analyze screenshot", "analyse screenshot", "analyze image", "analyse image"])
        return ["screenshot " + path if path else "screenshot"]

    # backtest / autonomous
    if any(x in t for x in ["backtest", "test strategy", "replay"]):
        syms = extract_symbols(t)
        return [f"backtest {s}" for s in syms] if syms else ["backtest gold"]
    if any(x in t for x in ["autonomous", "assistant mode", "monitor", "watch"]):
        syms = extract_symbols(t)
        return [f"autonomous {s}" for s in syms] if syms else ["autonomous gold"]

    # memory preferences
    if t.startswith("remember "):
        return [t]
    if any(x in t for x in ["memory", "preferences", "what do you remember"]):
        return ["memory"]

    # analysis / signal phrases. Can return multiple symbols.
    analysis_words = [
        "check", "analyse", "analyze", "analysis", "signal", "setup", "entry", "buy", "sell",
        "should i buy", "should i sell", "trade idea", "market read", "read", "look at",
        "what do you think", "your view", "is it good", "can i enter", "should i enter",
        "human analysis", "analyst view", "give me view", "market opinion"
    ]
    syms = extract_symbols(t)
    if syms and (any(w in t for w in analysis_words) or len(t.split()) <= 3):
        return [f"check {s}" for s in syms]

    # If phrase is just a symbol, analyze it.
    if syms:
        return [f"check {s}" for s in syms]

    return [t]



def _attach_style(commands: List[str], style: str) -> List[str]:
    """Append non-default style to market-analysis commands so the engine can choose the right execution profile."""
    if not style or style == DEFAULT_TRADE_STYLE:
        return commands
    out: List[str] = []
    for cmd in commands:
        if cmd.startswith(("check ", "autonomous ", "backtest ")) and style not in cmd:
            out.append(f"{cmd} {style}")
        else:
            out.append(cmd)
    return out

def parse_user_commands(text: str) -> List[str]:
    original = clean_text(text)
    requested_style = detect_trade_style(original)
    syms_all = extract_symbols(original)

    # Exact aliases must win before the broad natural-intent router.
    if original in QUICK_ALIASES:
        return [QUICK_ALIASES[original]]

    # Preserve Phase 15 file/path commands before symbol rewriting.
    if (original.startswith("mt5 learn history") or original.startswith("learn mt5 history") or
        original.startswith("backtest learn ") or original.startswith("backtest import ") or
        original in {"backtest template", "create backtest template", "journal learn history", "learning report", "phase15 status"}):
        return [original]

    # Backtest-all command contains commas/and words, so preserve it before splitting.
    if "backtest" in original and any(x in original for x in ["all", "csv", "cvs", "journal", "demo", "ml", "everything"]):
        return ["backtest learn all"]

    # Some commands naturally apply to many symbols in one phrase. Handle before splitting on "and".
    if syms_all and any(x in original for x in ["backtest", "test strategy", "replay"]):
        return _attach_style([f"backtest {s}" for s in syms_all], requested_style)
    if syms_all and any(x in original for x in ["autonomous", "assistant mode", "monitor", "watch"]):
        return _attach_style([f"autonomous {s}" for s in syms_all], requested_style)
    if len(syms_all) > 1 and any(x in original for x in ["check", "analyse", "analyze", "analysis", "signal", "setup", "entry", "market read", "look at", "swing", "scalping", "position", "intraday"]):
        return _attach_style([f"check {s}" for s in syms_all], requested_style)

    commands: List[str] = []
    for part in split_user_commands(text):
        natural_commands = infer_intent_commands(part)
        candidates = natural_commands if natural_commands else normalize_single_command(part)
        for cmd in candidates:
            if cmd and cmd not in commands:
                commands.append(cmd)
    return _attach_style(commands, requested_style) or [clean_text(text)]
