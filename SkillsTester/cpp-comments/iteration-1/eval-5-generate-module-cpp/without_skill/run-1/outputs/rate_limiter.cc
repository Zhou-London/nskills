// rate_limiter.cc
//
// Implementation of the TokenBucket rate limiter declared in rate_limiter.h.

#include "rate_limiter.h"

#include <algorithm>
#include <cassert>

namespace ratelimit {

TokenBucket::TokenBucket(double capacity, double refill_rate,
                         double initial_tokens)
    : capacity_(capacity),
      refill_rate_(refill_rate),
      tokens_(initial_tokens < 0.0
                  ? capacity
                  : std::min(initial_tokens, capacity)),
      last_refill_(Clock::now()) {
  assert(capacity > 0.0 && "capacity must be positive");
  assert(refill_rate > 0.0 && "refill_rate must be positive");
}

void TokenBucket::RefillLocked() {
  const Clock::time_point now = Clock::now();
  // Elapsed time since the last refill, in (fractional) seconds.
  const double elapsed =
      std::chrono::duration_cast<std::chrono::duration<double>>(
          now - last_refill_)
          .count();
  if (elapsed > 0.0) {
    // Accrue tokens for the elapsed interval, capping at capacity so that
    // idle periods cannot build up an unbounded burst.
    tokens_ = std::min(capacity_, tokens_ + elapsed * refill_rate_);
    last_refill_ = now;
  }
}

void TokenBucket::Acquire(double n) {
  if (n <= 0.0) {
    return;  // Nothing to acquire.
  }
  // A request larger than the bucket can ever hold would block forever;
  // clamp it so it is satisfiable from a full bucket.
  n = std::min(n, capacity_);

  std::unique_lock<std::mutex> lock(mu_);
  for (;;) {
    RefillLocked();
    if (tokens_ >= n) {
      tokens_ -= n;
      return;
    }
    // Not enough tokens yet. Compute how long until the deficit is refilled
    // and sleep for (at least) that long. wait_for releases the lock while
    // sleeping, so other threads can make progress.
    const double deficit = n - tokens_;
    const auto wait_time = std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double>(deficit / refill_rate_));
    // Wake either after the estimated refill time or when notified (e.g. by
    // a future API that returns tokens). Spurious wakeups are harmless: the
    // loop re-checks the token count before proceeding.
    cv_.wait_for(lock, wait_time);
  }
}

bool TokenBucket::TryAcquire(double n) {
  if (n <= 0.0) {
    return true;  // Nothing to acquire; trivially succeeds.
  }
  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked();
  if (tokens_ >= n) {
    tokens_ -= n;
    return true;
  }
  return false;
}

double TokenBucket::AvailableTokens() {
  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked();
  return tokens_;
}

}  // namespace ratelimit
