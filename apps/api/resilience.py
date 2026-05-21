"""Shared resilience utilities: retry with exponential backoff, Langfuse error logging."""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_status: tuple[int, ...] = (500, 502, 503, 504, 429),
    label: str = "request",
) -> T:
    """
    Call fn() up to `attempts` times. Retries on httpx.HTTPStatusError with retryable_status codes,
    or on httpx.TransportError (connection reset, timeout, etc.).
    Uses exponential backoff: delay = base_delay * 2^attempt, capped at max_delay.
    Raises the last exception if all attempts fail.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            return fn()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in retryable_status:
                last_exc = e
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    "[%s] HTTP %d — retry %d/%d in %.1fs",
                    label, status, attempt + 1, attempts, delay,
                )
                time.sleep(delay)
            else:
                raise  # non-retryable HTTP error — propagate immediately
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_exc = e
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                "[%s] Transport error (%s) — retry %d/%d in %.1fs",
                label, type(e).__name__, attempt + 1, attempts, delay,
            )
            time.sleep(delay)
        except Exception as e:
            raise  # non-HTTP exception — propagate immediately

    raise last_exc  # type: ignore[misc]


def log_langfuse_error(
    label: str,
    error: Exception,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log an error to Langfuse as a named event on the current observation span.
    Falls back to stderr if Langfuse is unavailable or not in an active trace.
    """
    try:
        from langfuse import get_client
        client = get_client()
        if client and hasattr(client, "event"):
            client.event(
                name=f"error_{label}",
                level="ERROR",
                metadata={"error": str(error), "type": type(error).__name__, **(context or {})},
            )
    except Exception:
        pass  # Langfuse unavailable — already logged to stderr below
    logger.error("[%s] %s: %s", label, type(error).__name__, error)
