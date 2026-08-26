# data/pipeline.py
"""High‑level pipeline that glues together connector, validator and storage.
It maintains connection state and provides a safe API for the rest of the system.
"""

import asyncio
import enum
import time
from datetime import datetime
from typing import Callable, Awaitable

import pandas as pd

from config.settings import HISTORICAL_LIMIT, LOG_LEVEL
from utils.logger import logger
from .base_connector import AbstractConnector
from .validator import validate_ohlcv, DataValidationError
from .storage import DataStore


class ConnectionState(enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    SAFE_MODE = "SAFE_MODE"


class DataPipeline:
    """Orchestrates the data flow for a single symbol / timeframe.

    Usage example::

        pipeline = DataPipeline(connector, symbol="BTC/USDT", timeframe="1m")
        await pipeline.run_historical()
        await pipeline.start_live()
    """

    def __init__(self, connector: AbstractConnector, symbol: str, timeframe: str) -> None:
        self.connector = connector
        self.symbol = symbol
        self.timeframe = timeframe
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.store = DataStore()
        self._live_task: asyncio.Task | None = None

    async def _set_state(self, new_state: ConnectionState) -> None:
        logger.info("State transition: %s → %s", self.state.value, new_state.value)
        self.state = new_state

    async def init(self) -> None:
        """Initialize storage (create tables) and ensure connector is ready."""
        await self.store.init_db()
        await self._set_state(ConnectionState.CONNECTED)

    async def run_historical(self) -> pd.DataFrame:
        """Download, validate and persist historical candles.
        Returns the cleaned DataFrame.
        """
        await self._set_state(ConnectionState.CONNECTED)
        logger.info("Fetching historical data for %s %s", self.symbol, self.timeframe)
        raw_df = await self.connector.fetch_historical(
            symbol=self.symbol,
            timeframe=self.timeframe,
            limit=HISTORICAL_LIMIT,
        )
        try:
            clean_df = validate_ohlcv(raw_df, self.timeframe)
        except DataValidationError as exc:
            logger.error("Validation failed: %s", exc)
            raise
        await self.store.save_historical(clean_df, self.symbol, self.timeframe)
        logger.info("Historical data ready – %d rows", len(clean_df))
        return clean_df

    async def _on_live_candle(self, candle_df: pd.DataFrame) -> None:
        """Callback invoked for each live candle.
        Validates, stores and logs the candle. Errors put the system into SAFE_MODE.
        """
        try:
            clean = validate_ohlcv(candle_df, self.timeframe)
            await self.store.append_live(clean, self.symbol, self.timeframe)
            logger.info(
                "Live candle stored – ts=%s price=%.2f",
                datetime.utcfromtimestamp(clean.at[0, "timestamp"] / 1000),
                clean.at[0, "close"],
            )
        except DataValidationError as exc:
            logger.error("Live candle validation error: %s – entering SAFE_MODE", exc)
            await self._set_state(ConnectionState.SAFE_MODE)
        except Exception as exc:
            logger.exception("Unexpected error processing live candle – entering SAFE_MODE")
            await self._set_state(ConnectionState.SAFE_MODE)

    async def start_live(self) -> None:
        """Start the live streaming loop in a background task.
        The task runs until `stop()` is called.
        """
        if self._live_task and not self._live_task.done():
            logger.warning("Live stream already running")
            return
        await self._set_state(ConnectionState.CONNECTED)
        logger.info("Starting live stream for %s %s", self.symbol, self.timeframe)
        self._live_task = asyncio.create_task(
            self.connector.stream_live(
                symbol=self.symbol,
                timeframe=self.timeframe,
                on_candle=self._on_live_candle,
            )
        )

    async def stop(self) -> None:
        """Gracefully stop the live stream and close resources."""
        if self._live_task:
            self._live_task.cancel()
            try:
                await self._live_task
            except asyncio.CancelledError:
                pass
        await self.connector.close()
        await self._set_state(ConnectionState.DISCONNECTED)
        logger.info("DataPipeline stopped for %s %s", self.symbol, self.timeframe)

    # Helper for external modules to query current state
    def is_safe_mode(self) -> bool:
        return self.state == ConnectionState.SAFE_MODE
