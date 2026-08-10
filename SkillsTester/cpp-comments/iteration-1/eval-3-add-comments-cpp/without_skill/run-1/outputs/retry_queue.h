#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// A time-based retry queue that tracks tasks awaiting (re)execution and
// applies exponential backoff to failed tasks.
//
// Each task is identified by a unique string id and carries an opaque
// payload pointer (the queue does not own the payload). Tasks become
// eligible to run at a scheduled "ready" time; failures push that time
// further out with exponentially increasing delays, and tasks that reach
// the maximum attempt count are dropped from the queue.
//
// All timestamps and delays are expressed in seconds; callers supply the
// current time explicitly, so the queue itself never reads a clock.
// This class is not thread-safe.
class RetryQueue {
 public:
  // Constructs a queue where each task may fail at most `max_attempts`
  // times before being dropped, and the first retry delay is
  // `base_delay_s` seconds (doubling on each subsequent failure).
  RetryQueue(int max_attempts, double base_delay_s);

  // Adds a new task that is immediately ready at time `now_s`.
  // The queue stores `payload` but does not take ownership of it.
  // Returns true if the task was added, or false if a task with the
  // same `task_id` already exists (the existing entry is left unchanged).
  bool Schedule(const std::string& task_id, void* payload, double now_s);

  // Returns the time (in seconds) at which the task becomes ready to run,
  // or -1.0 if no task with `task_id` is present in the queue.
  double NextReadyAt(const std::string& task_id) const;

  // Records a failed attempt for the task at current time `now_s`.
  //
  // If the task is still eligible for retry, reschedules it with
  // exponential backoff (base_delay_s * 2^(failures - 1)) and returns the
  // new ready time. Returns std::nullopt if the task does not exist or if
  // it has exhausted its attempts, in which case it is removed from the
  // queue.
  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  // Removes and returns all tasks whose ready time is at or before
  // `now_s`, as (task_id, payload) pairs. Tasks not yet ready remain in
  // the queue.
  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  // Bookkeeping for a single scheduled task.
  struct Entry {
    void* payload;      // Caller-owned opaque task data; not owned here.
    int failures;       // Number of failed attempts recorded so far.
    double ready_at_s;  // Earliest time (seconds) the task may run.
  };

  int max_attempts_;    // Failure count at which a task is dropped.
  double base_delay_s_; // Delay (seconds) before the first retry.
  std::map<std::string, Entry> entries_;  // Pending tasks keyed by task id.
};

#endif  // RETRY_QUEUE_H_
