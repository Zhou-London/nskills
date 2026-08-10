"""Token bucket rate limiter.

This module provides a thread-safe token bucket rate limiter suitable for
throttling operations such as API calls, message sends, or any resource
access that should be limited to a sustained rate with support for bursts.

The token bucket algorithm works as follows:

* A bucket holds up to ``capacity`` tokens.
* Tokens are added to the bucket continuously at ``rate`` tokens per second.
* Each operation consumes one or more tokens. If enough tokens are
  available, the operation may proceed immediately; otherwise the caller
  must wait (or fail fast) until the bucket refills.

Because the bucket can accumulate up to ``capacity`` tokens while idle,
short bursts of up to ``capacity`` operations are allowed, while the
long-term average throughput never exceeds ``rate`` operations per second.

Example:
    Basic usage, blocking until permitted::

        from rate_limiter import TokenBucket

        limiter = TokenBucket(rate=5.0, capacity=10)

        for item in work_items:
            limiter.acquire()          # blocks until a token is available
            process(item)

    Non-blocking usage::

        if limiter.try_acquire():
            process(item)
        else:
            drop_or_queue(item)

    Waiting with a timeout::

        if limiter.acquire(timeout=2.0):
            process(item)
        else:
            handle_timeout(item)

The implementation is lazy: tokens are not added by a background thread.
Instead, the current token count is recomputed from the elapsed time
whenever the bucket is consulted. This makes the limiter cheap to create
and free of background resources.
"""

from __future__ import annotations

import threading
import time
from typing import Callable


class TokenBucket:
    """A thread-safe token bucket rate limiter.

    Tokens accumulate in the bucket at a fixed ``rate`` (tokens per
    second) up to a maximum of ``capacity``. Callers consume tokens via
    :meth:`acquire` (blocking) or :meth:`try_acquire` (non-blocking).

    Attributes:
        rate: Refill rate in tokens per second (read-only property).
        capacity: Maximum number of tokens the bucket can hold
            (read-only property).

    Thread safety:
        All public methods are safe to call concurrently from multiple
        threads. Blocked callers are woken efficiently via a condition
        variable rather than busy-waiting.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        initial_tokens: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initializes the token bucket.

        Args:
            rate: Refill rate in tokens per second. Must be positive.
            capacity: Maximum number of tokens the bucket can hold, which
                also bounds the largest burst (and the largest single
                request). Must be positive.
            initial_tokens: Number of tokens the bucket starts with.
                Defaults to ``capacity`` (a full bucket). Must be within
                ``[0, capacity]``.
            clock: A callable returning the current time in seconds as a
                float. Defaults to :func:`time.monotonic`. Primarily
                useful for testing.

        Raises:
            ValueError: If ``rate`` or ``capacity`` is not positive, or if
                ``initial_tokens`` is outside ``[0, capacity]``.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate!r}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity!r}")
        if initial_tokens is None:
            initial_tokens = capacity
        if not 0 <= initial_tokens <= capacity:
            raise ValueError(
                f"initial_tokens must be within [0, {capacity}], "
                f"got {initial_tokens!r}"
            )

        self._rate = float(rate)
        self._capacity = float(capacity)
        self._clock = clock
        self._tokens = float(initial_tokens)
        self._last_refill = clock()
        # A condition variable lets blocked acquirers sleep until either
        # their computed refill deadline passes or another thread returns
        # tokens / changes state.
        self._cond = threading.Condition()

    @property
    def rate(self) -> float:
        """Refill rate in tokens per second."""
        return self._rate

    @property
    def capacity(self) -> float:
        """Maximum number of tokens the bucket can hold."""
        return self._capacity

    @property
    def tokens(self) -> float:
        """Current number of tokens available (refreshed on access).

        This value is advisory: in a multithreaded program another thread
        may consume tokens immediately after this property is read.
        """
        with self._cond:
            self._refill()
            return self._tokens

    def acquire(self, n: float = 1, timeout: float | None = None) -> bool:
        """Acquires ``n`` tokens, blocking until they are available.

        If the bucket currently holds at least ``n`` tokens, they are
        consumed and the method returns immediately. Otherwise the caller
        blocks until enough tokens have accumulated, or until ``timeout``
        expires.

        Args:
            n: Number of tokens to acquire. Must be positive and must not
                exceed the bucket's capacity (otherwise the request could
                never be satisfied).
            timeout: Maximum number of seconds to wait. ``None`` (the
                default) means wait indefinitely.

        Returns:
            True if the tokens were acquired. False only if ``timeout``
            was given and expired before enough tokens became available;
            in that case no tokens are consumed.

        Raises:
            ValueError: If ``n`` is not positive or exceeds ``capacity``.
        """
        self._validate_request(n)
        deadline = None if timeout is None else self._clock() + timeout

        with self._cond:
            while True:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True

                # Time until the bucket will (at the earliest) hold n
                # tokens, assuming no other consumers.
                wait_needed = (n - self._tokens) / self._rate
                if deadline is not None:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        return False
                    wait_needed = min(wait_needed, remaining)
                # Condition.wait releases the lock while sleeping, so
                # other threads may consume tokens in the meantime; the
                # loop re-checks availability after waking.
                self._cond.wait(wait_needed)

    def try_acquire(self, n: float = 1) -> bool:
        """Attempts to acquire ``n`` tokens without blocking.

        Args:
            n: Number of tokens to acquire. Must be positive and must not
                exceed the bucket's capacity.

        Returns:
            True if the tokens were available and have been consumed,
            False otherwise (no tokens are consumed on failure).

        Raises:
            ValueError: If ``n`` is not positive or exceeds ``capacity``.
        """
        self._validate_request(n)
        with self._cond:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def _validate_request(self, n: float) -> None:
        """Validates a token request size.

        Args:
            n: Requested number of tokens.

        Raises:
            ValueError: If ``n`` is not positive or exceeds ``capacity``.
        """
        if n <= 0:
            raise ValueError(f"n must be positive, got {n!r}")
        if n > self._capacity:
            raise ValueError(
                f"cannot acquire {n!r} tokens from a bucket with "
                f"capacity {self._capacity!r}"
            )

    def _refill(self) -> None:
        """Adds tokens accrued since the last refill.

        Must be called with ``self._cond`` held. Updates ``_tokens`` based
        on the elapsed time and clamps the result at ``_capacity``.
        """
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(
                self._capacity, self._tokens + elapsed * self._rate
            )
            self._last_refill = now

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(rate={self._rate!r}, "
            f"capacity={self._capacity!r}, tokens={self._tokens:.3f})"
        )
