#ifndef RETRY_QUEUE_H_
#define RETRY_QUEUE_H_

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

class RetryQueue {
 public:
  RetryQueue(int max_attempts, double base_delay_s);

  bool Schedule(const std::string& task_id, void* payload, double now_s);

  double NextReadyAt(const std::string& task_id) const;

  std::optional<double> MarkFailed(const std::string& task_id, double now_s);

  std::vector<std::pair<std::string, void*>> DrainReady(double now_s);

 private:
  struct Entry {
    void* payload;
    int failures;
    double ready_at_s;
  };

  int max_attempts_;
  double base_delay_s_;
  std::map<std::string, Entry> entries_;
};

#endif  // RETRY_QUEUE_H_
