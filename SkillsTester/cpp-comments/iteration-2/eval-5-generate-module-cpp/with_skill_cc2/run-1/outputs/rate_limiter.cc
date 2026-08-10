// Copyright 2026 The RateLimiter Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Implementation strategy: tokens are refilled lazily. No background thread
// runs; instead, every operation first computes how many tokens have accrued
// since the last accounting instant (`last_refill_`) from the elapsed time on
// a steady clock, credits them (capped at capacity), and only then checks
// availability. Blocked Acquire calls sleep on a condition variable with a
// deadline computed from the exact deficit, so they wake close to the moment
// enough tokens exist rather than polling.

#include "rate_limiter.h"

#include <cassert>
#include <chrono>
#include <mutex>

namespace rate_limiter {

TokenBucket::TokenBucket(int64_t capacity, double refill_rate)
    : capacity_(capacity),
      refill_rate_(refill_rate),
      // Start full so callers can burst immediately instead of stalling for
      // up to capacity/rate seconds right after construction.
      available_(static_cast<double>(capacity)),
      last_refill_(Clock::now()) {
  assert(capacity_ >= 1);
  assert(refill_rate_ > 0.0);
}

void TokenBucket::RefillLocked(Clock::time_point now) {
  // A steady clock never goes backwards, but guard anyway so a zero or
  // negative interval cannot drain the bucket.
  if (now <= last_refill_) return;
  const double elapsed_seconds =
      std::chrono::duration<double>(now - last_refill_).count();
  available_ += elapsed_seconds * refill_rate_;
  if (available_ > static_cast<double>(capacity_)) {
    available_ = static_cast<double>(capacity_);
  }
  // Advance the accounting instant even when the bucket capped out: time
  // spent full earns nothing, and leaving `last_refill_` behind would
  // double-count that idle interval on the next refill.
  last_refill_ = now;
}

void TokenBucket::Acquire(int64_t n) {
  assert(n >= 1);
  assert(n <= capacity_);  // Larger requests could never be satisfied.
  const double needed = static_cast<double>(n);

  std::unique_lock<std::mutex> lock(mu_);
  for (;;) {
    RefillLocked(Clock::now());
    if (available_ >= needed) {
      available_ -= needed;
      return;
    }
    // Sleep until roughly when the deficit will have refilled, rather than
    // waiting for a notification: tokens accrue from the passage of time
    // alone, so no other thread will necessarily signal us. cv_ still wakes
    // us early if a future API (e.g. returning tokens) adds them sooner, and
    // spurious wakeups are harmless because the loop re-checks from scratch.
    const double deficit = needed - available_;
    const auto wait = std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double>(deficit / refill_rate_));
    // Wait at least one tick so a sub-tick deficit does not degenerate into
    // a busy spin.
    cv_.wait_for(lock, wait > Clock::duration::zero()
                           ? wait
                           : Clock::duration(1));
  }
}

bool TokenBucket::TryAcquire(int64_t n) {
  assert(n >= 1);
  const double needed = static_cast<double>(n);

  std::lock_guard<std::mutex> lock(mu_);
  RefillLocked(Clock::now());
  if (available_ < needed) return false;
  available_ -= needed;
  return true;
}

}  // namespace rate_limiter
