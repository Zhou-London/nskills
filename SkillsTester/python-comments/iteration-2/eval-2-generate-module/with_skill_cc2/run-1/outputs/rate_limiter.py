"""A thread-safe token-bucket rate limiter.

A token bucket holds up to `capacity` tokens and refills continuously at
`rate` tokens per second. Each operation the caller wants to rate-limit
consumes one or more tokens; when the bucket is empty, callers either wait
for it to refill (`acquire`) or are refused immediately (`try_acquire`).
Because unused capacity accumulates (up to `capacity`), short bursts are
allowed while the long-run average rate stays at or below `rate`.

Typical usage example:

  bucket = TokenBucket(rate=10.0, capacity=20.0)

  # Blocking: waits until a token is available.
  bucket.acquire()
  handle_request()

  # Non-blocking: sheds load when the limit is exceeded.
  if bucket.try_acquire(5):
      handle_batch()
  else:
      reject_batch()
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A token-bucket rate limiter safe for use from multiple threads.

    The bucket starts full. Tokens accrue continuously (as a float, so
    fractional refill is not lost between calls) at `rate` tokens per
    second up to `capacity`, based on a monotonic clock, so the limiter
    is immune to wall-clock adjustments. All state is guarded by an
    internal lock; instances may be shared freely across threads.

    Waiting in `acquire` is implemented by sleeping for the exact time
    until enough tokens will have accrued, rather than polling, so
    blocked callers impose no busy-wait cost. Fairness across multiple
    blocked threads is not guaranteed: threads recheck the bucket when
    they wake, and an interleaving thread may take tokens first.

    Attributes:
        rate: Sustained refill rate, in tokens per second. Read-only.
        capacity: Maximum number of tokens the bucket can hold, which
            bounds the largest burst and the largest permissible request.
            Read-only.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        """Initializes a full bucket.

        Args:
            rate: Refill rate in tokens per second. Must be positive.
            capacity: Maximum tokens the bucket holds, and therefore the
                largest value ever acceptable as `n` in `acquire` or
                `try_acquire`. Must be positive.

        Raises:
            ValueError: If `rate` or `capacity` is not positive.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._rate = float(rate)
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        """Sustained refill rate, in tokens per second."""
        return self._rate

    @property
    def capacity(self) -> float:
        """Maximum number of tokens the bucket can hold."""
        return self._capacity

    def try_acquire(self, n: float = 1.0) -> bool:
        """Attempts to take `n` tokens without blocking.

        Either consumes all `n` tokens or consumes nothing, so a refused
        caller has not spent any of its budget.

        Args:
            n: Number of tokens to take. May be fractional. Must be
                positive and no greater than `capacity` (a larger request
                could never succeed, so it is rejected as a usage error
                rather than refused).

        Returns:
            True if the tokens were taken; False if fewer than `n` tokens
            are currently available.

        Raises:
            ValueError: If `n` is not positive or exceeds `capacity`.
        """
        self._check_request(n)
        with self._lock:
            self._refill_locked()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def acquire(self, n: float = 1.0, timeout: float | None = None) -> bool:
        """Takes `n` tokens, blocking until they are available.

        Tokens are consumed all-or-nothing: on timeout, nothing has been
        taken, so waiting never spends the caller's budget.

        Args:
            n: Number of tokens to take. May be fractional. Must be
                positive and no greater than `capacity` (a larger request
                could never be satisfied). Defaults to 1.
            timeout: Maximum seconds to wait. None (the default) waits
                indefinitely. A timeout of 0 behaves like `try_acquire`.

        Returns:
            True once the tokens have been taken; False if `timeout`
            elapsed first. Always True when `timeout` is None.

        Raises:
            ValueError: If `n` is not positive or exceeds `capacity`, or
                if `timeout` is negative.
        """
        self._check_request(n)
        if timeout is not None and timeout < 0:
            raise ValueError(f"timeout must be non-negative, got {timeout}")

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill_locked()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                # Sleep for exactly the time the deficit takes to refill,
                # computed while still holding the lock so the deficit is
                # consistent with the refill above.
                wait = (n - self._tokens) / self._rate

            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            # Another thread may take the tokens while we sleep, so the
            # loop rechecks availability rather than assuming success.
            time.sleep(wait)

    def _check_request(self, n: float) -> None:
        """Rejects token counts that are non-positive or can never fit."""
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if n > self._capacity:
            raise ValueError(
                f"cannot acquire {n} tokens from a bucket of capacity "
                f"{self._capacity}"
            )

    def _refill_locked(self) -> None:
        """Credits tokens accrued since the last refill. Caller holds the lock."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
