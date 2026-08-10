"""An in-memory queue of tasks retried with exponential backoff.

Tasks are scheduled with a payload, become ready immediately, and on each
failure are pushed back with a delay that doubles per attempt. A task that
fails max_attempts times is dropped. All timestamps use the time.monotonic
clock unless the caller supplies its own `now` values.

Typical usage example:

  queue = RetryQueue(max_attempts=3, base_delay=0.5)
  queue.schedule('task-1', payload)
  for task_id, payload in queue.drain_ready():
      if not process(payload):
          queue.mark_failed(task_id)
"""

import time


class RetryQueue:
    """Tracks pending tasks and reschedules failed ones with backoff.

    Each pending task carries its payload, a failure count, and the
    monotonic time at which it next becomes ready. The delay after the
    n-th failure is base_delay * 2**(n - 1), so retries back off
    exponentially until max_attempts failures permanently drop the task.

    Attributes:
        max_attempts: An integer for the number of failures allowed before
          a task is dropped.
        base_delay: A float for the delay in seconds applied after the
          first failure; later failures double it each time.
    """

    def __init__(self, max_attempts=3, base_delay=0.5):
        """Initializes the queue with retry limits.

        Args:
            max_attempts: An integer >= 1 giving the number of failures
              after which a task is dropped instead of rescheduled.
            base_delay: A float for the backoff delay, in seconds, after
              a task's first failure.

        Raises:
            ValueError: If max_attempts is less than 1.
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        # Maps task_id -> [payload, failure_count, ready_at_timestamp].
        self._pending = {}

    def schedule(self, task_id, payload, now=None):
        """Adds a task to the queue, ready to run immediately.

        Args:
            task_id: A hashable identifier for the task.
            payload: An arbitrary object handed back by drain_ready when
              the task is ready.
            now: An optional float timestamp to use as the ready time;
              defaults to time.monotonic().

        Returns:
            True if the task was added, False if task_id was already
            pending (in which case the existing entry is left untouched).
        """
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        """Returns the time at which a pending task becomes ready.

        Args:
            task_id: The identifier passed to schedule.

        Returns:
            A float monotonic timestamp at which the task is (or was)
            ready, or -1.0 if task_id is not pending.
        """
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        """Records a failure and reschedules or drops the task.

        The task's failure count is incremented. If it has now failed
        max_attempts times the task is removed; otherwise its ready time
        is pushed to now + base_delay * 2**(failures - 1).

        Args:
            task_id: The identifier of a currently pending task.
            now: An optional float timestamp from which to compute the
              backoff; defaults to time.monotonic().

        Returns:
            The new float ready time if the task was rescheduled, or None
            if it exhausted its attempts and was dropped.

        Raises:
            KeyError: If task_id is not pending.
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

        Yielded tasks are no longer pending, so a task must be
        re-scheduled (not merely marked failed) if the caller wants it
        retried after being drained. Tasks not yet ready are left in the
        queue untouched.

        Args:
            now: An optional float timestamp to compare ready times
              against; defaults to time.monotonic().

        Yields:
            (task_id, payload) tuples for each ready task, in arbitrary
            order.
        """
        now = time.monotonic() if now is None else now
        # Snapshot the keys: entries are deleted during iteration.
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
