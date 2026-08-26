# data/ccxt_connector.py
"""Concrete connector using CCXT for REST historical data and WebSocket live stream.
Supports automatic reconnection, exponential back‑off and timeout handling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Awaitable

import ccxt.async_support as ccxt
import pandas as pd

from config.settings import (
    CCXT_EXCHANGE,
    CCXT_API_KEY,
    CCXT_SECRET,
    CCXT_PASSWORD,
    REST_MAX_RETRIES,
    NETWORK_TIMEOUT,
)
from utils.helpers import retry_backoff
from utils.logger import logger
from .base_connector import AbstractConnector


class CCXTConnector(AbstractConnector):
    """CCXT implementation for a chosen exchange.

    The class creates a single async CCXT client instance. It provides
    `fetch_historical` and `stream_live` that conform to the abstract
    interface.
    """

    def __init__(self) -> None:
        self._exchange_name = CCXT_EXCHANGE.lower()
        # Dynamically instantiate the exchange class (e.g., ccxt.binance())
        exchange_cls = getattr(ccxt, self._exchange_name)
        self.exchange = exchange_cls({
            "apiKey": CCXT_API_KEY,
            "secret": CCXT_SECRET,
            "password": CCXT_PASSWORD,
            "enableRateLimit": True,
        })
        self._connected = False

    @property
    def name(self) -> str:
        return f"CCXT {self._exchange_name.title()}"

    async def _ensure_connection(self) -> None:
        if not self._connected:
            await self.exchange.load_markets()
            self._connected = True
            logger.info("CCXT connection established for %s", self._exchange_name)

    @retry_backoff(max_attempts=REST_MAX_RETRIES, initial_delay=1, max_delay=10)
    async def fetch_historical(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data with timeout and retry.

        Returns a DataFrame sorted by timestamp ascending.
        """
        await self._ensure_connection()
        try:
            raw = await asyncio.wait_for(
                self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit,
                ),
                timeout=NETWORK_TIMEOUT,
            )
        except Exception as exc:
            logger.exception("Failed to fetch historical data for %s", symbol)
            raise
        # Convert to DataFrame
        df = pd.DataFrame(
            raw,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        # Ensure integer timestamps (ms) and sort
        df["timestamp"] = df["timestamp"].astype(int)
        df = df.sort_values("timestamp").reset_index(drop=True)
        logger.debug("Fetched %d candles for %s %s", len(df), symbol, timeframe)
        return df

    async def stream_live(
        self,
        symbol: str,
        timeframe: str,
        on_candle: Callable[[pd.DataFrame], Awaitable[None]],
    ) -> None:
        """Subscribe to live candle updates via CCXT WebSocket (if supported).

        If the exchange does not provide a WebSocket via CCXT, we fall back
        to periodic REST polling (every `interval` seconds).
        """
        await self._ensure_connection()
        # Check if exchange has a websocket implementation
        ws_supported = getattr(self.exchange, "has", {}).get("ws", False)
        if ws_supported:
            await self._stream_via_ws(symbol, timeframe, on_candle)
        else:
            await self._fallback_polling(symbol, timeframe, on_candle)

    async def _stream_via_ws(
        self,
        symbol: str,
        timeframe: str,
        on_candle: Callable[[pd.DataFrame], Awaitable[None]],
    ) -> None:
        """Internal method using the exchange's native websocket client.
        This implementation follows CCXT's `watch_ohlcv` pattern.
        """
        logger.info("Starting WebSocket stream for %s %s via %s", symbol, timeframe, self.name)
        while True:
            try:
                ohlcv = await self.exchange.watch_ohlcv(symbol, timeframe)
                # `watch_ohlcv` returns the full list; the latest candle is the last element
                latest = ohlcv[-1]
                df = pd.DataFrame(
                    [latest],
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )
                await on_candle(df)
            except Exception as exc:
                logger.exception("WebSocket error, attempting reconnection...")
                # Simple reconnection logic – close and reopen the exchange client
                await self.exchange.close()
                self._connected = False
                await asyncio.sleep(1)  # short wait before retry
                await self._ensure_connection()

    async def _fallback_polling(
        self,
        symbol: str,
        timeframe: str,
        on_candle: Callable[[pd.DataFrame], Awaitable[None]],
    ) -> None:
        """Fallback to REST polling if websocket not available.
        Polls every `interval` seconds (configurable via env if needed).
        """
        interval = 5  # seconds – can be made configurable later
        logger.info(
            "WebSocket not supported for %s, using REST polling every %ds",
            self.name,
            interval,
        )
        last_ts = None
        while True:
            try:
                df = await self.fetch_historical(symbol, timeframe, limit=1)
                ts = df.at[0, "timestamp"]
                if ts != last_ts:
                    last_ts = ts
                    await on_candle(df)
            except Exception as exc:
                logger.exception("Polling error for %s", symbol)
            await asyncio.sleep(interval)

    async def close(self) -> None:
        """Close underlying CCXT client gracefully."""
        await self.exchange.close()
        self._connected = False
        logger.info("CCXT connector closed for %s", self._exchange_name)
