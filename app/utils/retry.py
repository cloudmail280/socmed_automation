"""Simple retry decorator with exponential backoff.

Dipakai di scrapers (flaky anti-bot) dan publishers (rate limit / hiccup
jaringan). Kita sengaja bikin kecil aja — cukup buat use case kita tanpa
nambah dep baru.
"""
from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Callable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


def retry(
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    jitter: float = 0.25,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry dekorator. Exponential backoff: base * 2**n + jitter (capped).

    Args:
        attempts: total upaya (termasuk yang pertama).
        base_delay: delay awal (detik).
        max_delay: batas atas delay per attempt.
        exceptions: tuple exception yang dianggap retryable.
        jitter: persentase jitter acak (0..1) untuk hindari thundering herd.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            last_exc: BaseException | None = None
            for n in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if n == attempts - 1:
                        break
                    delay = min(base_delay * (2**n), max_delay)
                    delay *= 1 + random.uniform(-jitter, jitter)
                    log.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.2fs",
                        fn.__name__,
                        n + 1,
                        attempts,
                        e,
                        delay,
                    )
                    time.sleep(max(0.0, delay))
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
