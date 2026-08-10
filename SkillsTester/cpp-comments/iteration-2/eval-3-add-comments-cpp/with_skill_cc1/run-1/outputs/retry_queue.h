#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

// Tracks tasks awaiting retry with exponential backoff: each failure delays a
// task by base_delay_s * 2^(failures - 1), and a task is dropped after
// max_attempts failures. Not thread-safe; callers must synchronize externally.
class RetryQueue {
 public:
  RetryQueue(int max_attempts, double base_delay_s);

  // Adds a task that is ready immediately at `now_s`. Returns false if
  // `task_id` is already queued. Does not take ownership of `payload`.
  bool Schedule(const std::string& task_id, void* payload, double now_s);

  // Returns the time (seconds) at which the task becomes ready, or -1.0 if
  // `task_id` is not queued.
  double NextReadyAt(const std::string& task_id) const;

  // Records a failure for the task and reschedules it with exponential
  // backoff, returning its new ready time. Returns nullopt if `task_id` is
  // unknown or the task reached max_attempts and was dropped.
  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  // Removes and returns all tasks whose ready time is at or before `now_s`.
  // Removed tasks are forgotten; re-add them with Schedule to retry again.
  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  // Per-task retry state.
  struct Entry {
    void* payload;  // Not owned.
    int failures;
    double ready_at_s;  // Earliest time (seconds) the task may be drained.
  };

  int max_attempts_;
  double base_delay_s_;
  // Queued tasks keyed by task id.
  std::map<std::string, Entry> entries_;
};

#endif  // RETRY_QUEUE_H_
