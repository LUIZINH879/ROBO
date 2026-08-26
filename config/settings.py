import os

# Leitor embutido de .env sem depender de bibliotecas externas
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

load_env_file()

# Exchange
CCXT_EXCHANGE = os.getenv("CCXT_EXCHANGE", "binance")
CCXT_API_KEY = os.getenv("CCXT_API_KEY", "")
CCXT_SECRET = os.getenv("CCXT_SECRET", "")
CCXT_PASSWORD = os.getenv("CCXT_PASSWORD", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///trading_bot.db")

# Historical & Network
HISTORICAL_LIMIT = int(os.getenv("HISTORICAL_LIMIT", "200"))
NETWORK_TIMEOUT = int(os.getenv("NETWORK_TIMEOUT", "15"))
REST_MAX_RETRIES = int(os.getenv("REST_MAX_RETRIES", "5"))

# Risk Management (ex: 0.00005 BTC ≈ R$ 5)
MAX_POSITION = float(os.getenv("MAX_POSITION", "0.00005"))
MAX_DRAWDOWN = float(os.getenv("MAX_DRAWDOWN", "0.30"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "trading_bot.log")
