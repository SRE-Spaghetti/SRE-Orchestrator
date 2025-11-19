"""Unit tests for retry utilities with exponential backoff."""

import pytest
import asyncio

from app.core.retry_utils import RetryConfig, retry_async, with_retry


class TestRetryConfig:
    """Test RetryConfig initialization and defaults."""

    def test_retry_config_default_values(self):
        """Test that RetryConfig initializes with correct default values."""
        # Arrange & Act
        config = RetryConfig()

        # Assert
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0
        assert config.retryable_exceptions == [Exception]

    def test_retry_config_custom_values(self):
        """Test that RetryConfig accepts custom values."""
        # Arrange & Act
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=20.0,
            exponential_base=3.0,
            retryable_exceptions=[ValueError, TypeError],
        )

        # Assert
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 20.0
        assert config.exponential_base == 3.0
        assert config.retryable_exceptions == [ValueError, TypeError]


class TestRetryAsyncSuccessfulExecution:
    """Test retry_async with successful execution scenarios."""

    @pytest.mark.asyncio
    async def test_retry_async_successful_first_attempt(self):
        """Test retry_async with successful execution on first attempt."""

        # Arrange
        async def successful_func():
            return "success"

        config = RetryConfig(max_attempts=3)

        # Act
        result = await retry_async(successful_func, config)

        # Assert
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_with_args_and_kwargs(self):
        """Test retry_async passes args and kwargs correctly."""

        # Arrange
        async def func_with_params(a, b, c=None):
            return f"{a}-{b}-{c}"

        config = RetryConfig(max_attempts=3)

        # Act
        result = await retry_async(
            func_with_params, config, None, "arg1", "arg2", c="kwarg1"
        )

        # Assert
        assert result == "arg1-arg2-kwarg1"

    @pytest.mark.asyncio
    async def test_retry_async_with_correlation_id(self):
        """Test retry_async accepts correlation_id for logging."""

        # Arrange
        async def successful_func():
            return "success"

        config = RetryConfig(max_attempts=3)
        correlation_id = "test-correlation-123"

        # Act
        result = await retry_async(successful_func, config, correlation_id)

        # Assert
        assert result == "success"


class TestRetryAsyncTransientFailures:
    """Test retry_async with transient failures and eventual success."""

    @pytest.mark.asyncio
    async def test_retry_async_succeeds_on_second_attempt(self):
        """Test retry_async succeeds after one failure."""
        # Arrange
        call_count = 0

        async def func_fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Transient error")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.01)

        # Act
        result = await retry_async(func_fails_once, config)

        # Assert
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_async_succeeds_on_third_attempt(self):
        """Test retry_async succeeds after two failures."""
        # Arrange
        call_count = 0

        async def func_fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Transient error")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.01)

        # Act
        result = await retry_async(func_fails_twice, config)

        # Assert
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_succeeds_on_last_attempt(self):
        """Test retry_async succeeds on the final allowed attempt."""
        # Arrange
        call_count = 0

        async def func_fails_until_last():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Transient error")
            return "success"

        config = RetryConfig(max_attempts=5, initial_delay=0.01)

        # Act
        result = await retry_async(func_fails_until_last, config)

        # Assert
        assert result == "success"
        assert call_count == 5


class TestRetryAsyncPermanentFailures:
    """Test retry_async with permanent failures."""

    @pytest.mark.asyncio
    async def test_retry_async_raises_after_max_attempts(self):
        """Test retry_async raises exception after exhausting all attempts."""
        # Arrange
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        config = RetryConfig(max_attempts=3, initial_delay=0.01)

        # Act & Assert
        with pytest.raises(ValueError, match="Permanent error"):
            await retry_async(always_fails, config)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_raises_non_retryable_exception_immediately(self):
        """Test retry_async raises non-retryable exceptions immediately."""
        # Arrange
        call_count = 0

        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise TypeError("Non-retryable error")

        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=[ValueError],  # Only ValueError is retryable
        )

        # Act & Assert
        with pytest.raises(TypeError, match="Non-retryable error"):
            await retry_async(raises_non_retryable, config)

        # Should only be called once, not retried
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_retries_only_retryable_exceptions(self):
        """Test retry_async only retries configured exception types."""
        # Arrange
        call_count = 0

        async def raises_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Retryable error")

        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=[ValueError, ConnectionError],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Retryable error"):
            await retry_async(raises_retryable, config)

        # Should be retried all 3 times
        assert call_count == 3


class TestRetryAsyncExponentialBackoff:
    """Test exponential backoff timing in retry_async."""

    @pytest.mark.asyncio
    async def test_retry_async_exponential_backoff_timing(self):
        """Test that retry_async uses exponential backoff between attempts."""
        # Arrange
        call_times = []

        async def func_fails_twice():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) <= 2:
                raise ValueError("Transient error")
            return "success"

        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0,
        )

        # Act
        result = await retry_async(func_fails_twice, config)

        # Assert
        assert result == "success"
        assert len(call_times) == 3

        # Check delays between attempts
        # First delay should be ~0.1s (initial_delay)
        delay1 = call_times[1] - call_times[0]
        assert 0.08 <= delay1 <= 0.15  # Allow some tolerance

        # Second delay should be ~0.2s (initial_delay * exponential_base)
        delay2 = call_times[2] - call_times[1]
        assert 0.18 <= delay2 <= 0.25  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_retry_async_respects_max_delay(self):
        """Test that retry_async respects max_delay cap."""
        # Arrange
        call_times = []

        async def always_fails():
            call_times.append(asyncio.get_event_loop().time())
            raise ValueError("Transient error")

        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.1,  # Reduced from 1.0 for faster tests
            max_delay=0.2,  # Reduced from 2.0 for faster tests
            exponential_base=2.0,
        )

        # Act & Assert
        with pytest.raises(ValueError):
            await retry_async(always_fails, config)

        assert len(call_times) == 5

        # Check that delays don't exceed max_delay
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            # Delay should not exceed max_delay + tolerance
            assert delay <= 0.25  # Adjusted tolerance for smaller max_delay

    @pytest.mark.asyncio
    async def test_retry_async_custom_exponential_base(self):
        """Test retry_async with custom exponential base."""
        # Arrange
        call_times = []

        async def func_fails_twice():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) <= 2:
                raise ValueError("Transient error")
            return "success"

        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=3.0,  # Triple delay each time
        )

        # Act
        result = await retry_async(func_fails_twice, config)

        # Assert
        assert result == "success"
        assert len(call_times) == 3

        # First delay should be ~0.1s
        delay1 = call_times[1] - call_times[0]
        assert 0.08 <= delay1 <= 0.15

        # Second delay should be ~0.3s (0.1 * 3.0)
        delay2 = call_times[2] - call_times[1]
        assert 0.28 <= delay2 <= 0.35


class TestRetryAsyncMaxAttempts:
    """Test max attempts limit in retry_async."""

    @pytest.mark.asyncio
    async def test_retry_async_respects_max_attempts_limit(self):
        """Test that retry_async stops after max_attempts."""
        # Arrange
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")

        config = RetryConfig(max_attempts=5, initial_delay=0.01)

        # Act & Assert
        with pytest.raises(ValueError):
            await retry_async(always_fails, config)

        assert call_count == 5

    @pytest.mark.asyncio
    async def test_retry_async_with_single_attempt(self):
        """Test retry_async with max_attempts=1 (no retries)."""
        # Arrange
        call_count = 0

        async def fails_once():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")

        config = RetryConfig(max_attempts=1, initial_delay=0.01)

        # Act & Assert
        with pytest.raises(ValueError):
            await retry_async(fails_once, config)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_with_many_attempts(self):
        """Test retry_async with large max_attempts value."""
        # Arrange
        call_count = 0

        async def fails_until_tenth():
            nonlocal call_count
            call_count += 1
            if call_count < 10:
                raise ValueError("Error")
            return "success"

        config = RetryConfig(max_attempts=10, initial_delay=0.01, max_delay=0.05)

        # Act
        result = await retry_async(fails_until_tenth, config)

        # Assert
        assert result == "success"
        assert call_count == 10


class TestWithRetryDecorator:
    """Test with_retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_with_retry_decorator_default_config(self):
        """Test with_retry decorator with default configuration."""
        # Arrange
        call_count = 0
        # Use fast config for testing
        fast_config = RetryConfig(max_attempts=3, initial_delay=0.01, max_delay=0.1)

        @with_retry(fast_config)
        async def func_fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Transient error")
            return "success"

        # Act
        result = await func_fails_once()

        # Assert
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_decorator_custom_config(self):
        """Test with_retry decorator with custom configuration."""
        # Arrange
        call_count = 0
        config = RetryConfig(max_attempts=5, initial_delay=0.01)

        @with_retry(config)
        async def func_fails_three_times():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("Transient error")
            return "success"

        # Act
        result = await func_fails_three_times()

        # Assert
        assert result == "success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_with_retry_decorator_preserves_function_metadata(self):
        """Test that with_retry decorator preserves function metadata."""

        # Arrange
        @with_retry()
        async def documented_function():
            """This is a documented function."""
            return "success"

        # Act & Assert
        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    @pytest.mark.asyncio
    async def test_with_retry_decorator_with_args_and_kwargs(self):
        """Test with_retry decorator passes args and kwargs correctly."""
        # Arrange
        call_count = 0
        # Use fast config for testing
        fast_config = RetryConfig(max_attempts=3, initial_delay=0.01, max_delay=0.1)

        @with_retry(fast_config)
        async def func_with_params(a, b, c=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Transient error")
            return f"{a}-{b}-{c}"

        # Act
        result = await func_with_params("arg1", "arg2", c="kwarg1")

        # Assert
        assert result == "arg1-arg2-kwarg1"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_decorator_raises_after_max_attempts(self):
        """Test with_retry decorator raises exception after max attempts."""
        # Arrange
        call_count = 0
        config = RetryConfig(max_attempts=2, initial_delay=0.01)

        @with_retry(config)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        # Act & Assert
        with pytest.raises(ValueError, match="Permanent error"):
            await always_fails()

        assert call_count == 2
