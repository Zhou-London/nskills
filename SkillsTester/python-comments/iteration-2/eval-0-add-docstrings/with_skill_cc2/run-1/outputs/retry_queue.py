"""An in-memory retry queue with exponential backoff scheduling.

Tracks pending tasks by id, records failed attempts, and computes when
each task next becomes eligible to run using exponential backoff. Tasks
that exhaust their attempt budget are dropped. Time is measured on the
`time.monotonic` clock unless the caller supplies explicit timestamps,
which makes the queue easy to drive deterministically in tests.

Typical usage example:

  queue = RetryQueue(max_attempts=3, base_delay=0.5)
  queue.schedule("job-1", {"url": "https://example.com"})
  for task_id, payload in queue.drain_ready():
      if not run(payload):
          queue.mark_failed(task_id)
"""

import time


class RetryQueue:
    """A queue of pending tasks retried with exponential backoff.

    Each scheduled task carries a payload, a failed-attempt count, and a
    timestamp before which it is not eligible to run. Failures push the
    task's ready time out by base_delay * 2**(attempts - 1); once a task
    accumulates max_attempts failures it is removed from the queue
    entirely. All methods accept an optional `now` timestamp so callers
    can supply their own clock; when omitted, `time.monotonic()` is used,
    so caller-supplied values must come from the same monotonic clock to
    compare meaningfully.

    This class is not thread-safe.

    Attributes:
        max_attempts: The number of failures allowed before a task is
            dropped from the queue.
        base_delay: The backoff delay in seconds after a task's first
            failure; subsequent failures double it.
    """

    def __init__(self, max_attempts=3, base_delay=0.5):
        """Initializes an empty queue with the given retry policy.

        Args:
            max_attempts: Maximum number of failures a task may accumulate
                before being dropped. Must be at least 1.
            base_delay: Backoff delay in seconds after the first failure;
                the delay doubles with each subsequent failure.

        Raises:
            ValueError: If max_attempts is less than 1.
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        # Maps task_id to a mutable [payload, attempts, ready_at] entry.
        self._pending = {}

    def schedule(self, task_id, payload, now=None):
        """Adds a task to the queue, ready to run immediately.

        The task starts with zero recorded failures and a ready time of
        `now`, so the next drain_ready call at or after that time will
        yield it. Scheduling is idempotent for a pending task: if task_id
        is already queued, the existing entry (including its attempt count
        and backoff) is left untouched.

        Args:
            task_id: Hashable identifier for the task, used as the queue
                key and returned by drain_ready.
            payload: Arbitrary task data handed back verbatim when the
                task is drained. The queue never inspects it.
            now: Timestamp at which the task becomes ready. Defaults to
                the current `time.monotonic()` reading.

        Returns:
            True if the task was newly scheduled; False if task_id was
            already pending and the call was a no-op.
        """
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        """Returns the timestamp at which a pending task becomes ready.

        Args:
            task_id: Identifier of the task to look up.

        Returns:
            The monotonic timestamp at or after which the task is eligible
            to be drained, or -1.0 if task_id is not pending (never
            scheduled, already drained, or dropped after exhausting its
            attempts).
        """
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        """Records a failed attempt and reschedules or drops the task.

        Increments the task's failure count. If the count reaches
        max_attempts, the task is permanently removed from the queue.
        Otherwise its ready time is pushed to now + base_delay *
        2**(attempts - 1), doubling the backoff with each failure.

        Args:
            task_id: Identifier of the pending task that failed.
            now: Timestamp the backoff is measured from. Defaults to the
                current `time.monotonic()` reading.

        Returns:
            The task's new ready timestamp if it was rescheduled, or None
            if it exhausted its attempts and was dropped from the queue.

        Raises:
            KeyError: If task_id is not currently pending.
        """
        now = time.monotonic() if now is None else now
        entry = self._pending[task_id]
        entry[1] += 1
        if entry[1] >= self.max_attempts:
            del self._pending[task_id]
            return None
        entry[2] = now + self.base_delay * (2 ** (entry[1] - 1))
        return entry[2]

    def drain_ready(self, now=None):
        """Yields and removes every task whose ready time has arrived.

        This is a generator: tasks are removed lazily as the caller
        iterates, so a partially consumed drain removes only the tasks
        already yielded. Readiness is judged against the single `now`
        value captured when iteration starts, not re-read per task.

        Args:
            now: Timestamp to compare ready times against. Defaults to
                the `time.monotonic()` reading taken at the first
                iteration step.

        Yields:
            (task_id, payload) pairs for each task whose ready time is at
            or before `now`, in the order the tasks were scheduled. Each
            yielded task is removed from the queue as it is produced.
        """
        now = time.monotonic() if now is None else now
        # Snapshot the keys so deleting entries mid-iteration is safe.
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
