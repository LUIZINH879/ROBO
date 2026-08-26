# data/validator.py
"""Data validation utilities for OHLCV DataFrames.
Ensures timestamps are monotonic, no duplicate candles, no gaps beyond allowed tolerance.
"""

import pandas as pd
from pandas import Timestamp
from typing import Tuple
import logging

from utils.logger import logger


class DataValidationError(Exception):
    """Raised when validation fails for a DataFrame."""


def _check_timestamp_monotonic(df: pd.DataFrame) -> None:
    if not df["timestamp"].is_monotonic_increasing:
        raise DataValidationError("Timestamps are not strictly increasing.")


def _check_duplicates(df: pd.DataFrame) -> None:
    dup = df.duplicated(subset=["timestamp"], keep=False)
    if dup.any():
        raise DataValidationError(f"Duplicate timestamps found: {df[dup]["timestamp"].tolist()}")


def _check_missing_candles(df: pd.DataFrame, timeframe_seconds: int) -> Tuple[pd.DataFrame, list[int]]:
    """Detect missing candles based on expected interval.
    Returns a cleaned DataFrame (with gaps filled as NaN rows) and a list of missing timestamps.
    """
    expected = pd.date_range(
        start=pd.to_datetime(df.iloc[0]["timestamp"], unit="ms"),
        end=pd.to_datetime(df.iloc[-1]["timestamp"], unit="ms"),
        freq=pd.Timedelta(seconds=timeframe_seconds),
    )
    existing = pd.to_datetime(df["timestamp"], unit="ms")
    missing = expected.difference(existing)
    if missing.empty:
        return df, []
    # Build missing rows with NaNs
    missing_df = pd.DataFrame({
        "timestamp": missing.astype(int) // 1_000_000,  # convert ns to ms
        "open": [float("nan")] * len(missing),
        "high": [float("nan")] * len(missing),
        "low": [float("nan")] * len(missing),
        "close": [float("nan")] * len(missing),
        "volume": [float("nan")] * len(missing),
    })
    combined = pd.concat([df, missing_df], ignore_index=True)
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined, missing.astype(int) // 1_000_000 .tolist()


def validate_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Validate an OHLCV DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        where timestamp is in milliseconds.
    timeframe : str
        CCXT timeframe string, e.g., '1m', '5m', '1h'. Used to compute expected gap.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame (duplicates removed, missing candles filled with NaN).
    """
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise DataValidationError(f"DataFrame missing required columns: {required - set(df.columns)}")

    # Ensure correct dtypes
    df = df.copy()
    df["timestamp"] = df["timestamp"].astype(int)
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # Basic checks
    _check_timestamp_monotonic(df)
    _check_duplicates(df)

    # Compute timeframe in seconds (CCXT: '1m' = 60, '1h' = 3600, etc.)
    unit = timeframe[-1]
    amount = int(timeframe[:-1])
    multiplier = {"m": 60, "h": 3600, "d": 86400, "w": 7 * 86400}[unit]
    timeframe_seconds = amount * multiplier

    cleaned_df, missing = _check_missing_candles(df, timeframe_seconds)
    if missing:
        logger.warning(
            "Missing %d candles detected for timeframe %s. Filled with NaN.",
            len(missing),
            timeframe,
        )
    return cleaned_df
