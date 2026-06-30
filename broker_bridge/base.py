"""Broker adapter interfaces for Blue Forex Market AI.

This layer keeps Blue broker-independent. MT5 brokers (Exness, XM, IC Markets,
Pepperstone, etc.) use the MetaTrader5 adapter. cTrader is included as a safe
scaffold because it requires cTrader Open API app credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class BrokerResult:
    ok: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class BrokerAdapter(Protocol):
    name: str
    platform: str

    def connect(self) -> BrokerResult: ...
    def account(self) -> BrokerResult: ...
    def positions(self) -> BrokerResult: ...
    def price(self, symbol: str) -> BrokerResult: ...
    def symbol_info(self, symbol: str) -> BrokerResult: ...
    def place_market_order(self, symbol: str, side: str, volume: float, sl: float, tp: float) -> BrokerResult: ...
    def close_position(self, ticket: int, partial_volume: Optional[float] = None) -> BrokerResult: ...
