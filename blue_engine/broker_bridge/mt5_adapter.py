"""MT5 adapter wrapping the existing Blue MT5 bridge."""
from __future__ import annotations

from typing import Optional

from broker_bridge.base import BrokerResult
from mt5_bridge import terminal


class MT5Adapter:
    name = "MetaTrader 5"
    platform = "mt5"

    def connect(self) -> BrokerResult:
        status = terminal.connect()
        return BrokerResult(status.ok, status.message)

    def account(self) -> BrokerResult:
        return BrokerResult(True, terminal.account_summary())

    def positions(self) -> BrokerResult:
        return BrokerResult(True, terminal.positions_text())

    def price(self, symbol: str) -> BrokerResult:
        return BrokerResult(True, terminal.live_price(symbol))

    def symbol_info(self, symbol: str) -> BrokerResult:
        return BrokerResult(True, terminal.symbol_info_text(symbol))

    def place_market_order(self, symbol: str, side: str, volume: float, sl: float, tp: float) -> BrokerResult:
        return BrokerResult(True, terminal.place_market_order(symbol, side, volume, sl, tp))

    def close_position(self, ticket: int, partial_volume: Optional[float] = None) -> BrokerResult:
        return BrokerResult(True, terminal.close_position(ticket, partial_volume=partial_volume))
