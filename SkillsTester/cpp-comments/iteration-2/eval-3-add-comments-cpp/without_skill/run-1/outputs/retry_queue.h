#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// A queue of tasks that are retried with exponential backoff.
//
// Each task is identified by a unique string id and carries an opaque
// payload pointer. When a task fails, its next-ready time is pushed out by
// base_delay_s * 2^(failures - 1); after max_attempts failures the task is
// dropped from the queue entirely. Tasks whose ready time has arrived can be
// collected (and removed) via DrainReady().
//
// All time values are absolute timestamps in seconds, supplied by the
// caller; the queue itself never reads a clock. This class is not
// thread-safe. It does not own the payload pointers.
class RetryQueue {
 public:
  // Constructs a queue that drops a task after `max_attempts` failures and
  // uses `base_delay_s` seconds as the initial backoff delay.
  RetryQueue(int max_attempts, double base_delay_s);

  // Adds a task to the queue, ready to run immediately at `now_s`.
  // Returns true if the task was added, or false if a task with the same
  // `task_id` is already queued (in which case nothing changes).
  bool Schedule(const std::string& task_id, void* payload, double now_s);

  // Returns the absolute time (in seconds) at which the given task becomes
  // ready to run, or -1.0 if the task is not in the queue.
  double NextReadyAt(const std::string& task_id) const;

  // Records a failure for the given task at time `now_s`.
  //
  // If the task's failure count reaches max_attempts, the task is removed
  // and std::nullopt is returned. Otherwise the task is rescheduled with
  // exponential backoff and its new ready time is returned. Also returns
  // std::nullopt if the task is not in the queue.
  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  // Removes and returns all tasks whose ready time is at or before `now_s`,
  // as (task_id, payload) pairs. Tasks not yet ready remain queued.
  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  // Bookkeeping for a single queued task.
  struct Entry {
    void* payload;      // Caller-owned, opaque task data.
    int failures;       // Number of failures recorded so far.
    double ready_at_s;  // Absolute time when the task is next ready to run.
  };

  // Number of failures after which a task is dropped.
  int max_attempts_;

  // Backoff delay, in seconds, applied after the first failure; doubles with
  // each subsequent failure.
  double base_delay_s_;

  // Queued tasks, keyed by task id.
  std::map<std::string, Entry> entries_;
};

#endif  // RETRY_QUEUE_H_
