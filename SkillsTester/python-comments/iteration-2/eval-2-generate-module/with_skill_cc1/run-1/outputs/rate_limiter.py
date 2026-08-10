"""Token-bucket rate limiter with blocking and non-blocking acquisition.

Typical usage example:

  bucket = TokenBucket(rate=10.0, capacity=20)
  bucket.acquire()          # blocks until a token is available
  if bucket.try_acquire(5): # returns immediately
      ...
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A thread-safe token-bucket rate limiter.

    Tokens accrue continuously at `rate` per second up to `capacity`;
    each acquisition spends tokens, so sustained throughput is bounded by
    `rate` while bursts up to `capacity` are allowed.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        """Initializes a full bucket.

        Args:
            rate: Token refill rate in tokens per second; must be positive.
            capacity: Maximum tokens the bucket holds; must be positive.

        Raises:
            ValueError: If rate or capacity is not positive.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        """The refill rate in tokens per second."""
        return self._rate

    @property
    def capacity(self) -> float:
        """The maximum number of tokens the bucket can hold."""
        return self._capacity

    def _refill(self) -> None:
        """Credits tokens accrued since the last refill. Caller holds the lock."""
        now = time.monotonic()
        self._tokens = min(
            self._capacity, self._tokens + (now - self._last_refill) * self._rate
        )
        self._last_refill = now

    def _check_amount(self, n: float) -> None:
        """Raises ValueError if `n` is not a satisfiable token amount."""
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if n > self._capacity:
            raise ValueError(
                f"n ({n}) exceeds bucket capacity ({self._capacity})"
            )

    def try_acquire(self, n: float = 1) -> bool:
        """Attempts to take `n` tokens without blocking.

        Args:
            n: Number of tokens to take; must be positive and at most capacity.

        Returns:
            True if the tokens were taken, False if too few are available.

        Raises:
            ValueError: If n is not positive or exceeds capacity.
        """
        self._check_amount(n)
        with self._lock:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def acquire(self, n: float = 1, timeout: float | None = None) -> bool:
        """Takes `n` tokens, blocking until they are available.

        Args:
            n: Number of tokens to take; must be positive and at most capacity.
            timeout: Maximum seconds to wait; None means wait indefinitely.

        Returns:
            True once the tokens are taken, False if the timeout expired first.

        Raises:
            ValueError: If n is not positive or exceeds capacity.
        """
        self._check_amount(n)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                # Sleep outside the lock for exactly the time the deficit
                # takes to refill, so waiters neither spin nor oversleep.
                wait = (n - self._tokens) / self._rate
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            time.sleep(wait)
