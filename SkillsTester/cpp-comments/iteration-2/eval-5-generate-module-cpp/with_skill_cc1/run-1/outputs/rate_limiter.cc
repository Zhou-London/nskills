#include "rate_limiter.h"

#include <algorithm>
#include <cassert>
#include <chrono>
#include <mutex>

namespace ratelimit {

TokenBucket::TokenBucket(double tokens_per_second, double capacity)
    : rate_(tokens_per_second),
      capacity_(capacity),
      tokens_(capacity),
      last_refill_(Clock::now()) {
  assert(rate_ > 0.0);
  assert(capacity_ > 0.0);
}

void TokenBucket::RefillLocked(Clock::time_point now) {
  const std::chrono::duration<double> elapsed = now - last_refill_;
  tokens_ = std::min(capacity_, tokens_ + elapsed.count() * rate_);
  last_refill_ = now;
}

bool TokenBucket::TryAcquire(double n) {
  assert(n >= 0.0);
  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked(Clock::now());
  if (tokens_ < n) return false;
  tokens_ -= n;
  return true;
}

void TokenBucket::Acquire(double n) {
  assert(n >= 0.0);
  assert(n <= capacity_);  // Larger requests can never be satisfied.
  std::unique_lock<std::mutex> lock(mu_);
  for (;;) {
    const Clock::time_point now = Clock::now();
    RefillLocked(now);
    if (tokens_ >= n) {
      tokens_ -= n;
      return;
    }
    // No other thread adds tokens; only time does. So rather than waiting for
    // a notification, sleep until the deficit will have accrued, then re-check
    // (another waiter may have drained the bucket in the meantime).
    const auto wait = std::chrono::duration<double>((n - tokens_) / rate_);
    cv_.wait_until(
        lock, now + std::chrono::duration_cast<Clock::duration>(wait));
  }
}

}  // namespace ratelimit
