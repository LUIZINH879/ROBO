# data/storage.py
"""Asynchronous storage layer for OHLCV data.
Uses SQLAlchemy with aiosqlite (or any DB URL) to store historical and live candles.
"""

import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Table, Column, Integer, Float, String, MetaData, insert, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_URL
from utils.logger import logger

metadata = MetaData()

ohlcv_historical = Table(
    "ohlcv_historical",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, index=True, nullable=False),
    Column("timeframe", String, index=True, nullable=False),
    Column("timestamp", Integer, index=True, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Float),
)

ohlcv_live = Table(
    "ohlcv_live",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String, index=True, nullable=False),
    Column("timeframe", String, index=True, nullable=False),
    Column("timestamp", Integer, index=True, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Float),
    Column("received_at", Integer, nullable=False),
)


class DataStore:
    """Simple async wrapper around the DB tables.
    Provides methods to save historical data and append live candles.
    """

    def __init__(self) -> None:
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.AsyncSession = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        logger.info("Database tables created / verified.")

    async def save_historical(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """Insert a whole historical DataFrame. If a candle already exists, it is ignored.
        """
        async with self.AsyncSession() as session:
            async with session.begin():
                rows = df.to_dict(orient="records")
                for row in rows:
                    stmt = sqlite_insert(ohlcv_historical).values(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=row["timestamp"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                    ).prefix_with("OR IGNORE")
                    await session.execute(stmt)
        logger.info("Saved %d historical candles for %s %s", len(df), symbol, timeframe)

    async def append_live(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """Append a single live candle (one‑row DataFrame)."""
        if df.shape[0] != 1:
            raise ValueError("append_live expects a single‑row DataFrame")
        row = df.iloc[0]
        async with self.AsyncSession() as session:
            async with session.begin():
                stmt = insert(ohlcv_live).values(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=row["timestamp"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    received_at=int(pd.Timestamp.utcnow().timestamp() * 1000),
                )
                await session.execute(stmt)
        logger.debug("Appended live candle timestamp %s for %s %s", row["timestamp"], symbol, timeframe)

    async def get_latest(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        """Return the most recent candle for a symbol/timeframe from live table."""
        async with self.AsyncSession() as session:
            stmt = (
                select(ohlcv_live)
                .where(ohlcv_live.c.symbol == symbol, ohlcv_live.c.timeframe == timeframe)
                .order_by(ohlcv_live.c.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row is None:
                return None
            df = pd.DataFrame([dict(row)], columns=row.keys())
            return df
