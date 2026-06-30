from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

SETTINGS_FILE = Path("broker_settings.json")

BROKER_PROFILES: Dict[str, Dict[str, Any]] = {
    "auto": {
        "label": "Auto Detect MT5 Broker",
        "suffix": "",
        "description": "Blue scans all MT5 symbols and auto-selects matching names. Best when changing broker frequently.",
        "symbol_map": {},
        "aliases": {},
    },
    "exness": {
        "label": "Exness MT5",
        "suffix": "m",
        "description": "Exness demo/standard style symbols such as XAUUSDm, EURUSDm, BTCUSDm.",
        "symbol_map": {
            "GC=F": "XAUUSDm", "SI=F": "XAGUSDm", "EURUSD=X": "EURUSDm", "GBPUSD=X": "GBPUSDm",
            "JPY=X": "USDJPYm", "BTC-USD": "BTCUSDm", "ETH-USD": "ETHUSDm", "CL=F": "USOILm",
            "NQ=F": "NAS100m", "ES=F": "US500m", "DX-Y.NYB": "DXYm",
        },
    },
    "xm": {
        "label": "XM / XMGlobal MT5",
        "suffix": "",
        "description": "XM usually exposes symbols such as EURUSD, GBPUSD, USDJPY, GOLD/XAUUSD depending on account type. Blue auto-discovers suffixes like .micro if present.",
        "symbol_map": {
            "GC=F": "GOLD", "SI=F": "SILVER", "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD",
            "JPY=X": "USDJPY", "BTC-USD": "BTCUSD", "ETH-USD": "ETHUSD", "CL=F": "OIL",
            "NQ=F": "US100", "ES=F": "US500", "DX-Y.NYB": "DXY",
        },
    },
    "icmarkets": {
        "label": "IC Markets MT5",
        "suffix": "",
        "description": "Generic IC Markets style. Blue auto-discovers exact symbols from Market Watch/all symbols.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"XTIUSD", "NQ=F":"USTEC", "ES=F":"US500"},
    },

    "pepperstone": {
        "label": "Pepperstone MT5",
        "suffix": "",
        "description": "Pepperstone MT5 style symbols. Blue also auto-discovers suffixes/prefixes from the broker symbol list.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"XTIUSD", "NQ=F":"NAS100", "ES=F":"US500"},
    },
    "octa": {
        "label": "Octa / OctaFX MT5",
        "suffix": "",
        "description": "Octa MT5 style. Exact names depend on account type, so Blue scans all broker symbols automatically.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"XTIUSD", "NQ=F":"NAS100", "ES=F":"US500"},
    },
    "fbs": {
        "label": "FBS MT5",
        "suffix": "",
        "description": "FBS MT5 style. Blue checks normal names plus broker-specific suffixes.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"USOIL", "NQ=F":"US100", "ES=F":"US500"},
    },
    "hfm": {
        "label": "HFM / HotForex MT5",
        "suffix": "",
        "description": "HFM MT5 style. Some accounts use suffixes; Blue auto-discovers from Market Watch/all symbols.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"USOIL", "NQ=F":"USA100", "ES=F":"USA500"},
    },
    "generic_mt5": {
        "label": "Generic MT5 Broker",
        "suffix": "",
        "description": "Use for any MT5 broker. Blue guesses symbols and scans the broker's symbol list.",
        "symbol_map": {"GC=F":"XAUUSD", "SI=F":"XAGUSD", "EURUSD=X":"EURUSD", "GBPUSD=X":"GBPUSD", "JPY=X":"USDJPY", "BTC-USD":"BTCUSD", "ETH-USD":"ETHUSD", "CL=F":"USOIL", "NQ=F":"NAS100", "ES=F":"US500"},
    },
    "ctrader": {
        "label": "cTrader / Open API scaffold",
        "suffix": "",
        "description": "Scaffold only. cTrader does not use MetaTrader5 Python package; real execution needs cTrader Open API credentials and adapter implementation.",
        "symbol_map": {},
    },
}

DEFAULT_ALIASES = {
    "XAUUSD": ["XAUUSD", "XAUUSDm", "xauusdm", "GOLD", "GOLDm", "GOLD#", "GOLDmicro", "XAUUSD.", "XAUUSD.a", "XAUUSD.r"],
    "XAGUSD": ["XAGUSD", "XAGUSDm", "SILVER", "SILVERm"],
    "EURUSD": ["EURUSD", "EURUSDm", "eurusdm", "EURUSD.", "EURUSDmicro", "EURUSD.a", "EURUSD.r"],
    "GBPUSD": ["GBPUSD", "GBPUSDm", "GBPUSD.", "GBPUSDmicro", "GBPUSD.a", "GBPUSD.r"],
    "USDJPY": ["USDJPY", "USDJPYm", "USDJPY.", "USDJPYmicro", "USDJPY.a", "USDJPY.r"],
    "BTCUSD": ["BTCUSD", "BTCUSDm", "BTC-USD", "BTCUSD.", "BTCUSD.a", "BTCUSD.r"],
    "ETHUSD": ["ETHUSD", "ETHUSDm", "ETH-USD", "ETHUSD.", "ETHUSD.a", "ETHUSD.r"],
    "USOIL": ["USOIL", "USOILm", "XTIUSD", "WTI", "WTIm", "OIL", "OILCash", "USOILCash"],
    "NAS100": ["NAS100", "NAS100m", "US100", "USTEC", "USTECm", "NAS100Cash", "US100Cash"],
    "US500": ["US500", "US500m", "SPX500", "SPX500m", "US500Cash", "SP500"],
    "DXY": ["DXY", "DXYm", "USDX"],
}


def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"platform": "mt5", "profile": "auto"}


def save_settings(platform: str = "mt5", profile: str = "auto") -> Dict[str, Any]:
    profile = (profile or "auto").lower().strip()
    platform = (platform or "mt5").lower().strip()
    if profile not in BROKER_PROFILES:
        raise ValueError(f"Unknown broker profile: {profile}")
    data = {"platform": platform, "profile": profile}
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def active_profile() -> Dict[str, Any]:
    data = load_settings()
    profile_name = data.get("profile", "auto")
    p = dict(BROKER_PROFILES.get(profile_name, BROKER_PROFILES["auto"]))
    p["name"] = profile_name
    p["platform"] = data.get("platform", "mt5")
    aliases = dict(DEFAULT_ALIASES)
    aliases.update(p.get("aliases", {}) or {})
    p["aliases"] = aliases
    return p


def broker_status_text() -> str:
    settings = load_settings()
    profile = active_profile()
    lines = [
        "Broker Adapter Status",
        f"Platform : {settings.get('platform', 'mt5')}",
        f"Profile  : {profile.get('name')} — {profile.get('label')}",
        f"Suffix   : {profile.get('suffix') or '(auto/no fixed suffix)'}",
        f"Note     : {profile.get('description', '')}",
        "",
        "Supported profiles: " + ", ".join(BROKER_PROFILES.keys()),
    ]
    if profile.get("name") == "ctrader":
        lines.append("cTrader note: this build includes a scaffold only. Real cTrader execution needs Open API credentials and a completed cTrader adapter.")
    return "\n".join(lines)


def set_broker_profile_text(profile: str) -> str:
    profile = (profile or "auto").lower().strip().replace(" ", "_")
    aliases = {"generic":"generic_mt5", "mt5":"generic_mt5", "auto_detect":"auto", "xmglobal":"xm", "hotforex":"hfm", "octafx":"octa", "ic":"icmarkets"}
    profile = aliases.get(profile, profile)
    if profile not in BROKER_PROFILES:
        return "Unknown broker profile. Use: broker set auto / exness / xm / icmarkets / pepperstone / octa / fbs / hfm / generic_mt5 / ctrader"
    platform = "ctrader" if profile == "ctrader" else "mt5"
    save_settings(platform=platform, profile=profile)
    return broker_status_text()
