"""Broker manager for selecting MT5/cTrader adapters."""
from __future__ import annotations

from broker_bridge.base import BrokerAdapter
from broker_bridge.mt5_adapter import MT5Adapter
from broker_bridge.ctrader_adapter import CTraderAdapter
from mt5_bridge.broker_profiles import active_profile


def get_active_adapter() -> BrokerAdapter:
    profile = active_profile()
    platform = (profile.get("platform") or "mt5").lower()
    if platform == "ctrader" or profile.get("name") == "ctrader":
        return CTraderAdapter()
    return MT5Adapter()


def active_adapter_status() -> str:
    adapter = get_active_adapter()
    result = adapter.connect()
    return f"Active adapter: {adapter.name} ({adapter.platform})\n{result.message}"
