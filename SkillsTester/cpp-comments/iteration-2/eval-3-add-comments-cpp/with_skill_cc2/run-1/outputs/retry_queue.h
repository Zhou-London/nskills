#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// Tracks tasks awaiting retry with exponential backoff and hands them back
// to the caller once their backoff delay has elapsed.
//
// Each task is identified by a caller-chosen string id and carries an opaque
// payload pointer. A newly scheduled task is ready immediately; every failure
// reported via MarkFailed() pushes its ready time further into the future,
// doubling the delay each time, until the task has failed `max_attempts`
// times and is dropped. The caller polls DrainReady() with the current time
// to collect the tasks whose delay has expired.
//
// Time is represented as seconds in an arbitrary caller-defined clock; the
// queue never reads a clock itself, it only compares the `now_s` values the
// caller passes in, so the caller must use one consistent, monotonic time
// source across all calls.
//
// The queue does not own the payload pointers. It never dereferences or
// frees them; the caller is responsible for keeping each payload alive until
// the task is returned by DrainReady() or dropped by MarkFailed(), and for
// releasing it afterwards.
//
// Not thread-safe. All calls on an instance must be externally synchronized
// or made from a single thread.
//
// Example:
//   RetryQueue queue(/*max_attempts=*/3, /*base_delay_s=*/1.0);
//   queue.Schedule("job-1", payload, now);
//   for (auto& [id, payload] : queue.DrainReady(now)) {
//     if (!Run(payload)) queue.Schedule(id, payload, now);  // Or MarkFailed.
//   }
class RetryQueue {
 public:
  // Creates an empty queue. A task is dropped once it has failed
  // `max_attempts` times, and the backoff after its Nth failure is
  // `base_delay_s * 2^(N-1)` seconds.
  RetryQueue(int max_attempts, double base_delay_s);

  // Adds a task that is ready immediately (at `now_s`) with a failure count
  // of zero. Returns true if the task was added, or false if a task with the
  // same `task_id` is already queued, in which case the existing entry is
  // left untouched and `payload` is not stored. Does not take ownership of
  // `payload`; the caller must keep it alive while the task is queued.
  bool Schedule(const std::string& task_id, void* payload, double now_s);

  // Returns the time (in the caller's clock, seconds) at which the task
  // becomes eligible for DrainReady(), or -1.0 if no task with `task_id` is
  // queued. The returned time may be in the past, meaning the task is ready
  // now.
  double NextReadyAt(const std::string& task_id) const;

  // Records one failure for the task. If the task has now failed
  // `max_attempts` times, removes it from the queue and returns std::nullopt;
  // the caller regains responsibility for the payload. Otherwise reschedules
  // the task with exponentially increasing backoff and returns its new ready
  // time. Also returns std::nullopt if `task_id` is not queued, so a nullopt
  // result alone does not distinguish "exhausted" from "unknown task".
  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  // Removes every task whose ready time is at or before `now_s` and returns
  // their (task_id, payload) pairs, ordered by task id. The returned tasks
  // are no longer tracked: to retry one of them later the caller must
  // Schedule() it again, which restarts its failure count from zero. Returns
  // an empty vector if nothing is ready. Cost is linear in the number of
  // queued tasks.
  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  // Per-task retry state, keyed by task id in `entries_`.
  struct Entry {
    // Caller-owned opaque payload; never dereferenced by the queue.
    void* payload;
    // Number of failures recorded so far via MarkFailed(). Always less than
    // max_attempts_ while the entry is queued; reaching it removes the entry.
    int failures;
    // Time (caller's clock, seconds) at which the task becomes eligible for
    // DrainReady().
    double ready_at_s;
  };

  // Failure count at which a task is dropped instead of rescheduled.
  int max_attempts_;
  // Backoff after the first failure, in seconds; doubles with each
  // subsequent failure.
  double base_delay_s_;
  // Queued tasks keyed by task id. std::map keeps ids ordered, which makes
  // DrainReady()'s output deterministic.
  std::map<std::string, Entry> entries_;
};

#endif  // RETRY_QUEUE_H_
