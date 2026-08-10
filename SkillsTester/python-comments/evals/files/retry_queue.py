import time


class RetryQueue:

    def __init__(self, max_attempts=3, base_delay=0.5):
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self._pending = {}

    def schedule(self, task_id, payload, now=None):
        now = time.monotonic() if now is None else now
        if task_id in self._pending:
            return False
        self._pending[task_id] = [payload, 0, now]
        return True

    def next_ready_at(self, task_id):
        try:
            return self._pending[task_id][2]
        except KeyError:
            return -1.0

    def mark_failed(self, task_id, now=None):
        now = time.monotonic() if now is None else now
        entry = self._pending[task_id]
        entry[1] += 1
        if entry[1] >= self.max_attempts:
            del self._pending[task_id]
            return None
        entry[2] = now + self.base_delay * (2 ** (entry[1] - 1))
        return entry[2]

    def drain_ready(self, now=None):
        now = time.monotonic() if now is None else now
        for task_id in list(self._pending):
            payload, _, ready_at = self._pending[task_id]
            if ready_at <= now:
                del self._pending[task_id]
                yield task_id, payload
