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

#ifndef RATE_LIMITER_H_
#define RATE_LIMITER_H_

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>

namespace rate_limiter {

// A token-bucket rate limiter.
//
// Conceptually, a bucket holds up to `capacity` tokens and is refilled
// continuously at `refill_rate` tokens per second. Each admitted operation
// consumes some number of tokens; when the bucket is empty, operations must
// either wait for tokens to accumulate (Acquire) or be rejected (TryAcquire).
// Because unused capacity accumulates up to `capacity`, callers may burst up
// to `capacity` tokens at once after an idle period, while the long-run
// admission rate never exceeds `refill_rate` tokens per second.
//
// Example — limit outbound requests to 100 QPS with bursts of up to 10:
//
//    TokenBucket bucket(/*capacity=*/10, /*refill_rate=*/100.0);
//    while (HasWork()) {
//      bucket.Acquire(1);  // Blocks until a token is available.
//      SendRequest();
//    }
//
// Thread safety: fully thread-safe. Any number of threads may call Acquire
// and TryAcquire concurrently on the same instance. Blocked Acquire calls
// are woken in no particular order (wakeup order is left to the underlying
// condition variable), so strict FIFO fairness across waiters is not
// guaranteed; under sustained contention a waiter requesting many tokens may
// be starved by waiters requesting few.
//
// Lifetime: the bucket must outlive every thread that is blocked inside
// Acquire. Destroying a TokenBucket while a thread is waiting in Acquire is
// undefined behavior; drain or stop callers first.
class TokenBucket {
 public:
  // Constructs a bucket that holds at most `capacity` tokens and refills at
  // `refill_rate` tokens per second. The bucket starts full, so up to
  // `capacity` tokens may be acquired immediately with no waiting.
  //
  // `capacity` must be at least 1 and `refill_rate` must be positive;
  // violating either precondition is undefined behavior (an assertion failure
  // in debug builds).
  TokenBucket(int64_t capacity, double refill_rate);

  // Not copyable or movable: the object owns synchronization primitives, and
  // waiting threads hold references to it.
  TokenBucket(const TokenBucket&) = delete;
  TokenBucket& operator=(const TokenBucket&) = delete;

  // Blocks the calling thread until `n` tokens are available, then consumes
  // them and returns. Never fails and never times out; if the bucket refills
  // slower than demand, the wait can be arbitrarily long.
  //
  // `n` must be between 1 and the bucket's capacity, inclusive. Requests
  // larger than the capacity can never be satisfied — the bucket cannot hold
  // that many tokens at once — so they are a precondition violation
  // (undefined behavior; an assertion failure in debug builds) rather than a
  // permanent hang.
  //
  // The n tokens are consumed atomically: the call either takes all n or
  // keeps waiting. It never removes a partial amount, so a blocked Acquire
  // does not reduce what concurrent TryAcquire callers can take.
  void Acquire(int64_t n);

  // Attempts to consume `n` tokens without blocking. Returns true and
  // consumes exactly `n` tokens if at least that many are currently
  // available; otherwise returns false and consumes nothing. The only
  // blocking is a brief internal mutex acquisition, never a wait for refill.
  //
  // `n` must be at least 1. Values greater than the capacity are permitted
  // and simply always return false.
  bool TryAcquire(int64_t n);

  // Returns the bucket's maximum token count, as passed to the constructor.
  int64_t capacity() const { return capacity_; }

  // Returns the refill rate in tokens per second, as passed to the
  // constructor.
  double refill_rate() const { return refill_rate_; }

 private:
  using Clock = std::chrono::steady_clock;

  // Adds tokens accrued since `last_refill_` to `available_`, capping at
  // `capacity_`, and advances `last_refill_` to `now`. Caller must hold
  // `mu_`.
  void RefillLocked(Clock::time_point now);

  const int64_t capacity_;    // Maximum tokens the bucket can hold; >= 1.
  const double refill_rate_;  // Refill rate in tokens per second; > 0.

  mutable std::mutex mu_;

  // Signaled whenever tokens are added, so blocked Acquire calls can
  // re-check availability. Guarded by `mu_`.
  std::condition_variable cv_;

  // Tokens currently available, in [0, capacity_]. Stored as a double so
  // that fractional tokens accrued between refills at non-integral rates are
  // not lost to truncation. Guarded by `mu_`.
  double available_;

  // Instant up to which refill has been accounted for; tokens earned after
  // this point have not yet been added to `available_`. Guarded by `mu_`.
  Clock::time_point last_refill_;
};

}  // namespace rate_limiter

#endif  // RATE_LIMITER_H_
