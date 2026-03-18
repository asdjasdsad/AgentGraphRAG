from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import TypeVar


T = TypeVar("T")


def retry(times: int = 3, delay: float = 0.2) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover
                    last_error = exc
                    if attempt < times - 1:
                        sleep(delay)
            raise last_error

        return wrapper

    return decorator
