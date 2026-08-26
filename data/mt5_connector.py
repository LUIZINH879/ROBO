# data/mt5_connector.py
"""Stub implementation for MetaTrader5 connector.
Future implementation will follow the same abstract interface.
"""

from typing import Callable, Awaitable
import pandas as pd

from .base_connector import AbstractConnector


class MetaTrader5Connector(AbstractConnector):
    def __init__(self) -> None:
        # Placeholder – real MT5 init will go here.
        raise NotImplementedError("MetaTrader5Connector is not yet implemented.")

    @property
    def name(self) -> str:
        return "MetaTrader5"

    async def fetch_historical(
        self, symbol: str, timeframe: str, since: int | None = None, limit: int | None = None
    ) -> pd.DataFrame:
        raise NotImplementedError("MetaTrader5 historical fetch not implemented.")

    async def stream_live(
        self, symbol: str, timeframe: str, on_candle: Callable[[pd.DataFrame], Awaitable[None]]
    ) -> None:
        raise NotImplementedError("MetaTrader5 live streaming not implemented.")
