# utils/logger.py
"""Centralized logger configuration.
All modules should import `logger` from this file.
"""

import logging
from pathlib import Path
import sys

from config.settings import LOG_LEVEL, LOG_FILE

def _ensure_log_dir(path: Path) -> None:
    """Create parent directory for the log file if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)

log_path = Path(LOG_FILE)
_ensure_log_dir(log_path)

# Basic formatter with timestamp, level, module and message
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# File handler
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setFormatter(formatter)

# Console handler (stderr)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(formatter)

# Root logger configuration
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[file_handler, console_handler],
)

# Export a module‑level logger for convenience
logger = logging.getLogger("trading_bot")
