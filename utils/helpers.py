import asyncio
import functools
from utils.logger import logger

def retry_backoff(max_attempts=5, initial_delay=1, max_delay=10):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error("Tentativa %d falhou: %s. Sem novas tentativas.", attempt, e)
                        raise
                    logger.warning("Tentativa %d falhou (%s). Nova tentativa em %ds...", attempt, e, delay)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
        return wrapper
    return decorator
