"""In-memory retry queue with exponential backoff scheduling.

This module provides :class:`RetryQueue`, a small utility for tracking
tasks that may fail and need to be retried. Each task is scheduled with a
payload, and on failure its next-ready time is pushed back using
exponential backoff (``base_delay * 2 ** (attempt - 1)``). Tasks that
exhaust their allowed attempts are dropped from the queue.

Timestamps are based on ``time.monotonic()`` by default, but every
time-sensitive method accepts an explicit ``now`` argument to make
testing deterministic.
"""

import time


class RetryQueue:
    """Tracks failing tasks and schedules retries with exponential backoff.

    Each pending task is keyed by a caller-supplied task ID and stores its
    payload, the number of failed attempts so far, and the earliest time it
    is ready to run. Tasks become ready immediately when scheduled; each
    recorded failure delays them further, doubling the delay per attempt,
    until ``max_attempts`` failures permanently evict the task.

    Attributes:
        max_attempts: Maximum number of attempts (initial try plus retries)
            before a task is dropped.
        base_delay: Delay in seconds applied after the first failure;
            subsequent failures double it.
    """

    def __init__(self, max_attempts=3, base_delay=0.5):
        """Initializes an empty retry queue.

        Args:
            max_attempts: Maximum attempts allowed per task. Must be >= 1.
            base_delay: Backoff delay in seconds after the first failure.

        Raises:
            ValueError: If ``max_attempts`` is less than 1.
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        # Maps task_id -> [payload, attempt_count, ready_at_timestamp].
        self._pending = {}

    def schedule(self, task_id, payload, now=None):
        """Adds a task to the queue, ready to run immediately.

        Args:
            task_id: Unique identifier for the task. Scheduling an ID that
                is already pending is a no-op.
            payload: Arbitrary data associated with the task, returned by
                :meth:`drain_ready`.
            now: Timestamp to use as the task's ready time. Defaults to
                ``time.monotonic()``.

        Returns:
            True if the task was newly scheduled, False if a task with the
            same ID was already pending.
        """
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        """Returns the time at which a pending task becomes ready.

        Args:
            task_id: Identifier of the task to look up.

        Returns:
            The task's ready timestamp, or -1.0 if the task is not pending.
        """
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        """Records a failed attempt and reschedules or evicts the task.

        The task's attempt count is incremented. If it has reached
        ``max_attempts``, the task is removed from the queue; otherwise its
        ready time is pushed back by an exponentially growing delay.

        Args:
            task_id: Identifier of the task that failed. Must be pending.
            now: Timestamp from which the backoff delay is computed.
                Defaults to ``time.monotonic()``.

        Returns:
            The task's new ready timestamp, or None if the task exhausted
            its attempts and was dropped.

        Raises:
            KeyError: If ``task_id`` is not currently pending.
        """
        now = time.monotonic() if now is None else now
        entry = self._pending[task_id]
        entry[1] += 1
        if entry[1] >= self.max_attempts:
            del self._pending[task_id]
            return None
        # Exponential backoff: base_delay after the first failure, doubling
        # with each subsequent failure.
        entry[2] = now + self.base_delay * (2 ** (entry[1] - 1))
        return entry[2]

    def drain_ready(self, now=None):
        """Removes and yields all tasks whose ready time has arrived.

        Tasks are removed from the queue as they are yielded, so a task
        that fails again must be re-scheduled via :meth:`schedule`.

        Args:
            now: Timestamp to compare ready times against. Defaults to
                ``time.monotonic()``.

        Yields:
            Tuples of ``(task_id, payload)`` for each ready task.
        """
        now = time.monotonic() if now is None else now
        # Snapshot the keys since entries are deleted during iteration.
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
