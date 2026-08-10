"""An in-memory retry queue with exponential backoff between attempts.

Typical usage example:

  queue = RetryQueue(max_attempts=3)
  queue.schedule("task-1", payload)
  for task_id, payload in queue.drain_ready():
      ...
"""

import time


class RetryQueue:
    """Tracks pending tasks and when each becomes ready to retry.

    Failed tasks are rescheduled with exponentially growing delays and
    dropped once they exhaust their attempts.

    Attributes:
        max_attempts: Number of failures allowed before a task is dropped.
        base_delay: Delay in seconds after the first failure; doubles on
          each subsequent failure.
    """

    def __init__(self, max_attempts=3, base_delay=0.5):
        """Initializes the queue with retry limits.

        Args:
            max_attempts: Failures allowed before a task is dropped; must
              be >= 1.
            base_delay: Backoff delay in seconds after the first failure.

        Raises:
            ValueError: If max_attempts is less than 1.
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        # Maps task_id to [payload, failure_count, ready_at].
        self._pending = {}

    def schedule(self, task_id, payload, now=None):
        """Adds a task to the queue, ready immediately.

        Args:
            task_id: Unique identifier for the task.
            payload: Opaque data yielded back by drain_ready.
            now: Timestamp to use as the ready time; defaults to
              time.monotonic().

        Returns:
            True if the task was added, False if task_id is already pending.
        """
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        """Returns the task's ready time, or -1.0 if task_id is not pending."""
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        """Records a failure and reschedules the task with backoff.

        Args:
            task_id: Identifier of a currently pending task.
            now: Timestamp the failure occurred; defaults to
              time.monotonic().

        Returns:
            The task's new ready time, or None if it exhausted its
            attempts and was dropped.

        Raises:
            KeyError: If task_id is not pending.
        """
        now = time.monotonic() if now is None else now
        entry = self._pending[task_id]
        entry[1] += 1
        if entry[1] >= self.max_attempts:
            del self._pending[task_id]
            return None
        # Exponential backoff: base_delay doubles with each failure.
        entry[2] = now + self.base_delay * (2 ** (entry[1] - 1))
        return entry[2]

    def drain_ready(self, now=None):
        """Removes and yields every task whose ready time has arrived.

        Args:
            now: Cutoff timestamp; defaults to time.monotonic().

        Yields:
            (task_id, payload) pairs for each ready task; yielded tasks
            are removed from the queue.
        """
        now = time.monotonic() if now is None else now
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
