#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// Tracks tasks that need to be retried with exponential backoff, keyed by a
// caller-chosen task id. Each failure doubles the delay before the task
// becomes ready again; after `max_attempts` failures the task is dropped.
// Time is supplied by the caller on every call (seconds, any consistent
// origin), so the queue never reads a clock itself.
//
// Example:
//    RetryQueue queue(/*max_attempts=*/5, /*base_delay_s=*/1.0);
//    queue.Schedule("job-42", payload, Now());
//    ...
//    for (auto& [task_id, payload] : queue.DrainReady(Now())) {
//      if (!Run(payload)) queue.Schedule(task_id, payload, Now());
//    }
//
// Not thread-safe: callers must serialize all access externally.
//
// The queue never owns `payload` pointers; the caller must keep each payload
// alive until the task is drained or dropped, and free it afterwards.
class RetryQueue {
 public:
  RetryQueue(int max_attempts, double base_delay_s);

  // Adds a task that is ready to run immediately (at `now_s`). Returns false
  // and leaves the existing entry untouched if `task_id` is already queued.
  // Does not take ownership of `payload`.
  bool Schedule(const std::string& task_id, void* payload, double now_s);

  // Returns the time (in seconds) at which the task becomes eligible for
  // DrainReady, or -1.0 if `task_id` is not queued.
  double NextReadyAt(const std::string& task_id) const;

  // Records a failure for the task and reschedules it with exponential
  // backoff: base_delay_s * 2^(failures - 1) seconds after `now_s`. Returns
  // the new ready time, or std::nullopt if the task is unknown or has now
  // reached `max_attempts` and been dropped. A dropped task's payload is not
  // returned; the caller is responsible for cleaning it up.
  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  // Removes and returns every task whose ready time is at or before `now_s`,
  // as (task_id, payload) pairs. Returned tasks are forgotten unless the
  // caller re-Schedules them. O(n) in the number of queued tasks.
  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  // Per-task retry state.
  struct Entry {
    void* payload;      // Not owned.
    int failures;       // Failures recorded so far; 0 for a fresh task.
    double ready_at_s;  // Earliest time DrainReady may return this task.
  };

  int max_attempts_;     // Failure count at which a task is dropped.
  double base_delay_s_;  // Backoff delay after the first failure, in seconds.
  std::map<std::string, Entry> entries_;  // Queued tasks, keyed by task id.
};

#endif  // RETRY_QUEUE_H_
