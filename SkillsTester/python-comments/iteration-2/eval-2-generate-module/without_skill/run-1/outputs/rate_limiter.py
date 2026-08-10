"""Token-bucket rate limiter.

This module provides :class:`TokenBucket`, a thread-safe implementation of
the classic token-bucket rate limiting algorithm.

A token bucket holds up to ``capacity`` tokens.  Tokens are replenished
continuously at a fixed ``rate`` (tokens per second).  Each operation that
should be rate limited consumes one or more tokens:

* If enough tokens are available, the operation proceeds immediately.
* Otherwise, the caller may either wait until enough tokens accumulate
  (:meth:`TokenBucket.acquire`) or fail fast without blocking
  (:meth:`TokenBucket.try_acquire`).

Because tokens accumulate while the bucket is idle (up to ``capacity``),
the token bucket permits short bursts of activity while still enforcing
the configured average rate over time.

Example:
    Limit an operation to 5 calls per second, with bursts of up to 10::

        from rate_limiter import TokenBucket

        bucket = TokenBucket(rate=5, capacity=10)

        # Blocking usage -- waits until a token is available.
        bucket.acquire()
        do_rate_limited_work()

        # Non-blocking usage -- returns immediately.
        if bucket.try_acquire():
            do_rate_limited_work()
        else:
            print("rate limit exceeded, try again later")
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A thread-safe token-bucket rate limiter.

    The bucket starts full (``capacity`` tokens) and is refilled
    continuously at ``rate`` tokens per second.  Refilling is computed
    lazily from elapsed time on each acquisition attempt, so no background
    thread or timer is required.

    Attributes:
        rate: The refill rate, in tokens per second.
        capacity: The maximum number of tokens the bucket can hold.

    Thread safety:
        All public methods are safe to call concurrently from multiple
        threads.  Internal state is protected by a lock, and blocked
        ``acquire`` calls are woken via a condition variable whenever
        tokens may have become available.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        clock=time.monotonic,
    ) -> None:
        """Initializes a full token bucket.

        Args:
            rate: Refill rate in tokens per second.  Must be positive.
            capacity: Maximum number of tokens the bucket can hold (also
                the maximum burst size).  Must be positive.
            clock: A zero-argument callable returning the current time in
                seconds as a float.  Defaults to :func:`time.monotonic`.
                Primarily useful for injecting a fake clock in tests.

        Raises:
            ValueError: If ``rate`` or ``capacity`` is not positive.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate!r}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity!r}")

        self.rate = float(rate)
        self.capacity = float(capacity)

        self._clock = clock
        self._tokens = self.capacity  # Bucket starts full.
        self._last_refill = self._clock()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    @property
    def tokens(self) -> float:
        """The number of tokens currently available.

        This is a snapshot; in a multi-threaded program the value may be
        stale by the time the caller uses it.

        Returns:
            The current token count, between 0 and ``capacity``.
        """
        with self._lock:
            self._refill()
            return self._tokens

    def acquire(self, n: float = 1, timeout: float | None = None) -> bool:
        """Acquires ``n`` tokens, blocking until they are available.

        If the bucket does not currently hold ``n`` tokens, this method
        sleeps until enough tokens have been refilled (or until
        ``timeout`` elapses, if given).  Waiting threads are served
        as tokens become available; fairness among multiple waiters is
        not guaranteed.

        Args:
            n: Number of tokens to acquire.  Must be positive and must
                not exceed ``capacity`` (otherwise the request could
                never be satisfied).  Defaults to 1.
            timeout: Maximum number of seconds to wait.  ``None`` (the
                default) means wait indefinitely.

        Returns:
            True if the tokens were acquired, False if ``timeout``
            elapsed before enough tokens became available.

        Raises:
            ValueError: If ``n`` is not positive, exceeds ``capacity``,
                or if ``timeout`` is negative.
        """
        self._validate_request(n)
        if timeout is not None and timeout < 0:
            raise ValueError(f"timeout must be non-negative, got {timeout!r}")

        deadline = None if timeout is None else self._clock() + timeout

        with self._condition:
            while True:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True

                # Time until enough tokens will have been refilled.
                wait = (n - self._tokens) / self.rate
                if deadline is not None:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        return False
                    wait = min(wait, remaining)

                # Sleep until tokens should be available (or another
                # thread notifies us), then re-check under the lock.
                self._condition.wait(wait)

    def try_acquire(self, n: float = 1) -> bool:
        """Attempts to acquire ``n`` tokens without blocking.

        Args:
            n: Number of tokens to acquire.  Must be positive and must
                not exceed ``capacity``.  Defaults to 1.

        Returns:
            True if the tokens were available and have been consumed,
            False if there were not enough tokens (in which case no
            tokens are consumed).

        Raises:
            ValueError: If ``n`` is not positive or exceeds ``capacity``.
        """
        self._validate_request(n)

        with self._lock:
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
        if n > self.capacity:
            raise ValueError(
                f"cannot acquire {n!r} tokens from a bucket with "
                f"capacity {self.capacity!r}"
            )

    def _refill(self) -> None:
        """Adds tokens accrued since the last refill.

        Must be called with the lock held.  Updates ``_tokens`` based on
        the elapsed time and ``rate``, capping at ``capacity``.
        """
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_refill = now
