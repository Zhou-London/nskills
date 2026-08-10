#include "rate_limiter.h"

#include <algorithm>
#include <cassert>

TokenBucket::TokenBucket(double tokens_per_second, double capacity)
    : rate_(tokens_per_second),
      capacity_(capacity),
      tokens_(capacity),  // Start full so initial bursts are not throttled.
      last_refill_(std::chrono::steady_clock::now()) {
  assert(tokens_per_second > 0.0);
  assert(capacity > 0.0);
}

void TokenBucket::RefillLocked(std::chrono::steady_clock::time_point now) {
  // Tokens accrue lazily: instead of a background refill thread, each
  // caller computes how many tokens the elapsed time is worth. This keeps
  // the limiter passive (no threads of its own) at the cost of one clock
  // read per operation.
  const std::chrono::duration<double> elapsed = now - last_refill_;
  tokens_ = std::min(capacity_, tokens_ + elapsed.count() * rate_);
  last_refill_ = now;
}

void TokenBucket::Acquire(double n) {
  assert(n > 0.0);
  assert(n <= capacity_);
  std::unique_lock<std::mutex> lock(mu_);
  for (;;) {
    const auto now = std::chrono::steady_clock::now();
    RefillLocked(now);
    if (tokens_ >= n) {
      tokens_ -= n;
      return;
    }
    // Refill is driven purely by the passage of time, so we can compute
    // exactly when the deficit will be covered and sleep until then rather
    // than polling. wait_for releases `mu_`, letting other threads make
    // progress; re-checking in a loop handles the case where a concurrent
    // caller consumed the tokens we were waiting for.
    const auto wait = std::chrono::duration<double>((n - tokens_) / rate_);
    cv_.wait_for(
        lock,
        std::chrono::duration_cast<std::chrono::steady_clock::duration>(wait));
  }
}

bool TokenBucket::TryAcquire(double n) {
  assert(n > 0.0);
  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked(std::chrono::steady_clock::now());
  if (tokens_ < n) return false;
  tokens_ -= n;
  return true;
}
