# utils/helpers.py
"""General helper utilities used across the project.
- `retry_backoff` – decorator for exponential backoff retries.
- `chunks` – split iterable into fixed‑size chunks (useful for bulk DB inserts).
"""

import asyncio
import functools
import random
import time
from typing import Callable, Coroutine, TypeVar, Any

T = TypeVar("T")

def retry_backoff(
    max_attempts: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Async decorator that retries a coroutine with exponential back‑off.

    Args:
        max_attempts: Maximum number of attempts (including the first call).
        initial_delay: Base delay in seconds for the first retry.
        max_delay: Upper bound for the delay.
        jitter: Add random jitter to avoid thundering herd.
        exceptions: Exception types that trigger a retry.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            delay = initial_delay
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    if jitter:
                        jitter_val = random.uniform(0, delay)
                    else:
                        jitter_val = 0
                    await asyncio.sleep(delay + jitter_val)
                    delay = min(delay * 2, max_delay)
        return wrapper
    return decorator


def chunks(iterable, size: int):
    """Yield successive *size*-ed chunks from *iterable*.
    Useful for batch inserting into databases.
    """
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
