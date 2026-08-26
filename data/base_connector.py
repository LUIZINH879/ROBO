# data/base_connector.py
"""Abstract base class for data connectors.
All concrete connectors (CCXT, MetaTrader5, etc.) must implement the
asynchronous methods defined here.
"""

import abc
from typing import Callable, Awaitable
import pandas as pd


class AbstractConnector(abc.ABC):
    """Interface for fetching historical and live OHLCV data.

    Implementations must be asynchronous and raise appropriate exceptions
    on network errors.
    """

    @abc.abstractmethod
    async def fetch_historical(
        self, symbol: str, timeframe: str, since: int | None = None, limit: int | None = None
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data.

        Returns a DataFrame with columns:
        ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def stream_live(
        self,
        symbol: str,
        timeframe: str,
        on_candle: Callable[[pd.DataFrame], Awaitable[None]],
    ) -> None:
        """Continuously stream live candles.

        `on_candle` is an async callback that receives a single‑row DataFrame
        for each new candle.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human readable connector name (e.g., "CCXT Binance")."""
        raise NotImplementedError
