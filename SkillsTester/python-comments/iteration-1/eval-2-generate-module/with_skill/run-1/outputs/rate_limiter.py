"""A thread-safe token-bucket rate limiter.

The bucket holds up to a fixed capacity of tokens and refills at a
constant rate. Each operation consumes tokens; when the bucket runs dry,
callers either block until enough tokens accrue (`acquire`) or fail fast
(`try_acquire`). Bursts up to the bucket capacity are allowed after idle
periods, while the long-run rate never exceeds the refill rate.

Typical usage example:

  limiter = TokenBucket(rate=10.0, capacity=20)
  limiter.acquire()            # Blocks until one token is available.
  if limiter.try_acquire(5):   # Never blocks.
      send_batch(items[:5])
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A token bucket that limits the rate of some repeated operation.

    Tokens accrue continuously at `rate` per second up to `capacity`.
    The bucket starts full, so an initial burst of up to `capacity`
    operations is permitted. All methods are safe to call from multiple
    threads.

    Attributes:
        rate: The refill rate, in tokens per second.
        capacity: The maximum number of tokens the bucket can hold, and
          therefore the largest request that can ever succeed.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        """Initializes a full bucket.

        Args:
            rate: Refill rate in tokens per second. Must be positive.
            capacity: Maximum number of tokens the bucket holds. Must be
              positive.

        Raises:
            ValueError: If rate or capacity is not positive.
        """
        if rate <= 0:
            raise ValueError(f'rate must be positive, got {rate}')
        if capacity <= 0:
            raise ValueError(f'capacity must be positive, got {capacity}')
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, n: float = 1, timeout: float | None = None) -> bool:
        """Takes n tokens, blocking until they are available.

        Competing callers are not queued fairly: when tokens become
        available, whichever waiter wakes first takes them.

        Args:
            n: Number of tokens to take. Must be positive and no larger
              than the bucket capacity, since a larger request could
              never be satisfied.
            timeout: Maximum time in seconds to wait. None means wait
              indefinitely.

        Returns:
            True if the tokens were acquired, False if the timeout
            expired first. Always True when timeout is None.

        Raises:
            ValueError: If n is not positive or exceeds the bucket
              capacity.
        """
        self._check_request(n)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                # Time until the deficit refills at the current rate.
                wait = (n - self._tokens) / self.rate
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            # Sleep outside the lock so other threads can take or return
            # tokens meanwhile; the loop re-checks availability on wake.
            time.sleep(wait)

    def try_acquire(self, n: float = 1) -> bool:
        """Takes n tokens if they are available, without blocking.

        Args:
            n: Number of tokens to take. Must be positive and no larger
              than the bucket capacity.

        Returns:
            True if the tokens were taken, False if the bucket does not
            currently hold n tokens. Nothing is consumed on failure.

        Raises:
            ValueError: If n is not positive or exceeds the bucket
              capacity.
        """
        self._check_request(n)
        with self._lock:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    @property
    def available(self) -> float:
        """Returns the number of tokens currently in the bucket."""
        with self._lock:
            self._refill()
            return self._tokens

    def _check_request(self, n: float) -> None:
        """Validates a token request against the bucket's limits.

        Args:
            n: The requested token count.

        Raises:
            ValueError: If n is not positive or exceeds the bucket
              capacity.
        """
        if n <= 0:
            raise ValueError(f'token count must be positive, got {n}')
        if n > self.capacity:
            raise ValueError(
                f'requested {n} tokens, but capacity is {self.capacity}'
            )

    def _refill(self) -> None:
        """Adds tokens accrued since the last refill. Caller holds _lock."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
