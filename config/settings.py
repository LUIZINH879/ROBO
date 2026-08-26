# config/settings.py
"""Central configuration loaded from environment variables.
Provides defaults and type hints for all configurable parameters.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

# ---- Exchange configuration ----
CCXT_EXCHANGE = os.getenv("CCXT_EXCHANGE", "binance")  # default exchange for CCXT
CCXT_API_KEY = os.getenv("CCXT_API_KEY", "")
CCXT_SECRET = os.getenv("CCXT_SECRET", "")
CCXT_PASSWORD = os.getenv("CCXT_PASSWORD", "")  # some exchanges need a password

# ---- Database configuration ----
# SQLite for local dev, can be overridden with a PostgreSQL URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / "trading_bot.db"}"
)

# ---- Data pipeline configuration ----
# Number of historical candles to fetch on start
HISTORICAL_LIMIT = int(os.getenv("HISTORICAL_LIMIT", "5000"))
# WebSocket reconnect back‑off parameters (seconds)
WS_RETRY_INITIAL = float(os.getenv("WS_RETRY_INITIAL", "1"))
WS_RETRY_MAX = float(os.getenv("WS_RETRY_MAX", "30"))
# Maximum retry attempts for REST calls
REST_MAX_RETRIES = int(os.getenv("REST_MAX_RETRIES", "5"))
# Timeout for network calls (seconds)
NETWORK_TIMEOUT = float(os.getenv("NETWORK_TIMEOUT", "10"))

# ---- Logging configuration ----
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "trading_bot.log"))
