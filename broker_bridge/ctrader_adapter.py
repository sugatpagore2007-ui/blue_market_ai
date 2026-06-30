"""cTrader Open API adapter scaffold for Blue Forex Market AI.

Important: this file is intentionally safe. Unlike MT5, cTrader does not work
through the MetaTrader5 Python package. Live cTrader trading needs:
- cTrader Open API application client id / secret
- OAuth access token / refresh token
- cTrader account id
- symbol lookup using cTrader symbol ids
- order execution through cTrader protobuf/Open API messages

This scaffold lets the project select a cTrader profile and keeps all execution
blocked until real Open API credentials and implementation are added.
"""
from __future__ import annotations

import os
from typing import Optional

from broker_bridge.base import BrokerResult


class CTraderAdapter:
    name = "cTrader Open API"
    platform = "ctrader"

    def __init__(self) -> None:
        self.client_id = os.getenv("CTRADER_CLIENT_ID", "")
        self.client_secret = os.getenv("CTRADER_CLIENT_SECRET", "")
        self.access_token = os.getenv("CTRADER_ACCESS_TOKEN", "")
        self.account_id = os.getenv("CTRADER_ACCOUNT_ID", "")

    def _not_ready(self, action: str) -> BrokerResult:
        missing = [k for k, v in {
            "CTRADER_CLIENT_ID": self.client_id,
            "CTRADER_CLIENT_SECRET": self.client_secret,
            "CTRADER_ACCESS_TOKEN": self.access_token,
            "CTRADER_ACCOUNT_ID": self.account_id,
        }.items() if not v]
        msg = (
            f"cTrader {action} is not enabled yet. "
            "This build includes the adapter scaffold only. "
            "Add cTrader Open API credentials and implement the Open API request methods first."
        )
        if missing:
            msg += " Missing env values: " + ", ".join(missing)
        return BrokerResult(False, msg)

    def connect(self) -> BrokerResult:
        return self._not_ready("connect")

    def account(self) -> BrokerResult:
        return self._not_ready("account")

    def positions(self) -> BrokerResult:
        return self._not_ready("positions")

    def price(self, symbol: str) -> BrokerResult:
        return self._not_ready(f"price for {symbol}")

    def symbol_info(self, symbol: str) -> BrokerResult:
        return self._not_ready(f"symbol info for {symbol}")

    def place_market_order(self, symbol: str, side: str, volume: float, sl: float, tp: float) -> BrokerResult:
        return self._not_ready("order execution")

    def close_position(self, ticket: int, partial_volume: Optional[float] = None) -> BrokerResult:
        return self._not_ready("position close")


def ctrader_status() -> str:
    result = CTraderAdapter().connect()
    return (
        "cTrader Adapter Status\n"
        "Mode: scaffold / execution blocked\n"
        "Why: cTrader needs Open API OAuth credentials and symbol-id mapping.\n"
        f"Status: {result.message}\n"
        "Use now: broker set ctrader, then ctrader status. For live trading, complete the adapter implementation first."
    )
