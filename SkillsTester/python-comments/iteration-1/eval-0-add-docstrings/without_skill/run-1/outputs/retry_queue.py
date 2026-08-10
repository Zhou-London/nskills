"""A simple in-memory retry queue with exponential backoff.

Tasks are scheduled with a payload and become "ready" at a given time.
When a task fails, it is rescheduled with an exponentially increasing
delay (``base_delay * 2 ** (attempts - 1)``) until it exceeds the
maximum number of attempts, at which point it is dropped.

Timestamps are based on ``time.monotonic()`` by default, but every
time-sensitive method accepts an explicit ``now`` argument to make
testing deterministic.
"""

import time


class RetryQueue:
    """Tracks pending tasks and reschedules failed ones with backoff.

    Attributes:
        max_attempts: Maximum number of failed attempts before a task
            is permanently dropped from the queue.
        base_delay: Base delay in seconds used for exponential backoff.
    """

    def __init__(self, max_attempts=3, base_delay=0.5):
        """Initializes the queue.

        Args:
            max_attempts: Maximum failed attempts allowed per task.
                Must be at least 1.
            base_delay: Base backoff delay in seconds; the delay after
                the Nth failure is ``base_delay * 2 ** (N - 1)``.

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
        """Adds a new task to the queue, ready immediately.

        Args:
            task_id: Unique identifier for the task.
            payload: Arbitrary data associated with the task.
            now: Timestamp to use as the task's ready time. Defaults to
                ``time.monotonic()``.

        Returns:
            True if the task was scheduled, False if a task with the
            same ``task_id`` is already pending.
        """
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        """Returns the timestamp at which a task becomes ready.

        Args:
            task_id: Identifier of the task to look up.

        Returns:
            The monotonic timestamp when the task is ready to run, or
            -1.0 if the task is not pending.
        """
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        """Records a failed attempt and reschedules the task with backoff.

        If the task has reached ``max_attempts`` failures, it is removed
        from the queue permanently.

        Args:
            task_id: Identifier of the task that failed.
            now: Timestamp of the failure. Defaults to
                ``time.monotonic()``.

        Returns:
            The new ready timestamp for the task, or None if the task
            exhausted its attempts and was dropped.

        Raises:
            KeyError: If ``task_id`` is not pending.
        """
        now = time.monotonic() if now is None else now
        entry = self._pending[task_id]
        entry[1] += 1
        if entry[1] >= self.max_attempts:
            del self._pending[task_id]
            return None
        # Exponential backoff: delay doubles with each failed attempt.
        entry[2] = now + self.base_delay * (2 ** (entry[1] - 1))
        return entry[2]

    def drain_ready(self, now=None):
        """Yields and removes all tasks that are ready to run.

        Args:
            now: Timestamp to compare ready times against. Defaults to
                ``time.monotonic()``.

        Yields:
            Tuples of ``(task_id, payload)`` for each task whose ready
            time is at or before ``now``. Yielded tasks are removed from
            the queue; re-add them via ``mark_failed``/``schedule`` as
            appropriate.
        """
        now = time.monotonic() if now is None else now
        # Iterate over a snapshot of keys since we delete during iteration.
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
