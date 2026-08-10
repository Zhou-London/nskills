// rate_limiter.cc
//
// Implementation of the TokenBucket rate limiter declared in rate_limiter.h.

#include "rate_limiter.h"

#include <algorithm>
#include <cassert>
#include <cmath>

namespace ratelimit {

TokenBucket::TokenBucket(int64_t capacity, double refill_rate_per_sec)
    : capacity_(capacity),
      refill_rate_per_sec_(refill_rate_per_sec),
      // Start with a full bucket so callers can burst immediately.
      tokens_(static_cast<double>(capacity)),
      last_refill_(Clock::now()) {
  assert(capacity > 0 && "TokenBucket capacity must be positive");
  assert(refill_rate_per_sec > 0.0 && "TokenBucket refill rate must be positive");
}

void TokenBucket::RefillLocked(Clock::time_point now) {
  // The clock is monotonic, but guard against a zero/negative interval anyway
  // (e.g. two calls landing on the same tick).
  if (now <= last_refill_) return;

  const std::chrono::duration<double> elapsed = now - last_refill_;
  tokens_ = std::min(static_cast<double>(capacity_),
                     tokens_ + elapsed.count() * refill_rate_per_sec_);
  last_refill_ = now;
}

void TokenBucket::Acquire(int64_t n) {
  assert(n >= 1 && "Acquire: n must be at least 1");
  assert(n <= capacity_ && "Acquire: n must not exceed capacity");
  // In release builds, clamp instead of blocking forever on an impossible
  // request.
  n = std::max<int64_t>(1, std::min(n, capacity_));

  const double needed = static_cast<double>(n);
  std::unique_lock<std::mutex> lock(mu_);
  for (;;) {
    RefillLocked(Clock::now());
    if (tokens_ >= needed) {
      tokens_ -= needed;
      return;
    }

    // Not enough tokens yet. Compute how long the refill will take to cover
    // the deficit and sleep for that long instead of busy-polling. We use
    // wait_for (not an unconditional sleep) so that a notify from TryAcquire
    // failing/other bookkeeping or spurious wakeups simply re-run the loop,
    // which re-checks the balance under the lock.
    const double deficit = needed - tokens_;
    const auto wait_time = std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double>(deficit / refill_rate_per_sec_));
    // Wait at least one tick so we never spin with a zero timeout due to
    // floating-point truncation.
    cv_.wait_for(lock, std::max(wait_time, Clock::duration(1)));
  }
}

bool TokenBucket::TryAcquire(int64_t n) {
  assert(n >= 1 && "TryAcquire: n must be at least 1");
  if (n < 1) return false;
  // A request larger than capacity can never be satisfied.
  if (n > capacity_) return false;

  const double needed = static_cast<double>(n);
  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked(Clock::now());
  if (tokens_ < needed) return false;
  tokens_ -= needed;
  return true;
}

int64_t TokenBucket::AvailableTokens() const {
  std::lock_guard<std::mutex> lock(mu_);
  // Bring the balance up to date before reporting it. RefillLocked is
  // non-const because it mutates tokens_/last_refill_, so replicate the
  // computation on a copy here to keep this accessor const.
  const std::chrono::duration<double> elapsed = Clock::now() - last_refill_;
  const double current =
      std::min(static_cast<double>(capacity_),
               tokens_ + std::max(0.0, elapsed.count()) * refill_rate_per_sec_);
  // Report whole tokens only; fractional accrual is an implementation detail.
  return static_cast<int64_t>(std::floor(current));
}

}  // namespace ratelimit
