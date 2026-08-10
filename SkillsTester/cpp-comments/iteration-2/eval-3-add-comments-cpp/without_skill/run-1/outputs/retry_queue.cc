#include "retry_queue.h"

RetryQueue::RetryQueue(int max_attempts, double base_delay_s)
    : max_attempts_(max_attempts), base_delay_s_(base_delay_s) {}

bool RetryQueue::Schedule(const std::string& task_id, void* payload,
                          double now_s) {
  // try_emplace leaves the map untouched if the key already exists, so a
  // duplicate Schedule() call cannot clobber an existing entry's state.
  auto [it, inserted] =
      entries_.try_emplace(task_id, Entry{payload, 0, now_s});
  (void)it;
  return inserted;
}

double RetryQueue::NextReadyAt(const std::string& task_id) const {
  auto it = entries_.find(task_id);
  if (it == entries_.end()) return -1.0;
  return it->second.ready_at_s;
}

std::optional<double> RetryQueue::MarkFailed(const std::string& task_id,
                                             double now_s) {
  auto it = entries_.find(task_id);
  if (it == entries_.end()) return std::nullopt;
  Entry& entry = it->second;
  ++entry.failures;
  // Give up on the task once it has exhausted its attempts.
  if (entry.failures >= max_attempts_) {
    entries_.erase(it);
    return std::nullopt;
  }
  // Exponential backoff: delay of base_delay_s after the first failure,
  // doubling with each subsequent one.
  entry.ready_at_s = now_s + base_delay_s_ * (1 << (entry.failures - 1));
  return entry.ready_at_s;
}

std::vector<std::pair<std::string, void*>> RetryQueue::DrainReady(
    double now_s) {
  std::vector<std::pair<std::string, void*>> ready;
  for (auto it = entries_.begin(); it != entries_.end();) {
    if (it->second.ready_at_s <= now_s) {
      ready.emplace_back(it->first, it->second.payload);
      // erase() returns the next iterator, keeping the loop valid.
      it = entries_.erase(it);
    } else {
      ++it;
    }
  }
  return ready;
}
