import time
from typing import Callable, Iterable, TypeVar

from src.core.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def call_with_retries(
    operation: Callable[[], T],
    attempts: int,
    backoff_seconds: float,
    retry_on: Iterable[type[BaseException]],
    description: str,
) -> T:
    # used for surviving the transient mongo and minio failures that would otherwise kill a partition
    retryable = tuple(retry_on)
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retryable as error:
            last_error = error
            if attempt == attempts:
                break
            delay = backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "storage_call_retrying",
                extra={"operation": description, "attempt": attempt, "delay_seconds": delay, "reason": str(error)},
            )
            time.sleep(delay)
    raise RuntimeError(f"{description} failed after {attempts} attempts") from last_error
