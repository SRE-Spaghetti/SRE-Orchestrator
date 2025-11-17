"""
Retry utilities for error recovery in the SRE Orchestrator.

This module provides retry logic with exponential backoff for LLM calls
and other operations that may fail transiently.
"""

import logging
import asyncio
from typing import Any, Callable, Optional, TypeVar, List
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Optional[List[type]] = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            retryable_exceptions: List of exception types that should trigger retry
                                 If None, all exceptions are retryable
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or [Exception]


async def retry_async(
    func: Callable[..., Any],
    config: RetryConfig,
    correlation_id: Optional[str] = None,
    *args,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to retry
        config: Retry configuration
        correlation_id: Optional correlation ID for logging
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function execution

    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None
    delay = config.initial_delay

    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.info(
                "Attempting operation",
                extra={
                    "correlation_id": correlation_id,
                    "function": func.__name__,
                    "attempt": attempt,
                    "max_attempts": config.max_attempts,
                },
            )

            result = await func(*args, **kwargs)

            if attempt > 1:
                logger.info(
                    "Operation succeeded after retry",
                    extra={
                        "correlation_id": correlation_id,
                        "function": func.__name__,
                        "attempt": attempt,
                    },
                )

            return result

        except Exception as e:
            last_exception = e

            # Check if this exception is retryable
            is_retryable = any(
                isinstance(e, exc_type) for exc_type in config.retryable_exceptions
            )

            if not is_retryable:
                logger.error(
                    "Non-retryable exception occurred",
                    extra={
                        "correlation_id": correlation_id,
                        "function": func.__name__,
                        "attempt": attempt,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

            if attempt < config.max_attempts:
                logger.warning(
                    "Operation failed, will retry",
                    extra={
                        "correlation_id": correlation_id,
                        "function": func.__name__,
                        "attempt": attempt,
                        "max_attempts": config.max_attempts,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "retry_delay": delay,
                    },
                )

                await asyncio.sleep(delay)

                # Calculate next delay with exponential backoff
                delay = min(delay * config.exponential_base, config.max_delay)
            else:
                logger.error(
                    "Operation failed after all retry attempts",
                    extra={
                        "correlation_id": correlation_id,
                        "function": func.__name__,
                        "attempt": attempt,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

    # All retries exhausted
    raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration. If None, uses default configuration.

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract correlation_id from kwargs
            correlation_id = kwargs.get("correlation_id")

            return await retry_async(func, config, correlation_id, *args, **kwargs)

        return wrapper

    return decorator
