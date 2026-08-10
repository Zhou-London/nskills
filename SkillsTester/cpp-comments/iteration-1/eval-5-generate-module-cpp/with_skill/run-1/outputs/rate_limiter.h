#ifndef RATE_LIMITER_H_
#define RATE_LIMITER_H_

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>

// A token-bucket rate limiter.
//
// The bucket holds up to `capacity` tokens and refills continuously at
// `tokens_per_second`. Each operation consumes tokens; when the bucket is
// empty, callers either block until enough tokens accumulate (Acquire) or
// fail immediately (TryAcquire). Unused capacity accumulates, so short
// bursts up to `capacity` are allowed after an idle period.
//
// Example:
//    TokenBucket limiter(/*tokens_per_second=*/100.0, /*capacity=*/100.0);
//    for (const Request& request : requests) {
//      limiter.Acquire();  // Blocks until we are allowed to proceed.
//      Handle(request);
//    }
//
// Thread-safe: any number of threads may call Acquire() and TryAcquire()
// concurrently on the same instance. Tokens are granted to blocked callers
// in no particular order (no FIFO fairness guarantee).
class TokenBucket {
 public:
  // `tokens_per_second` and `capacity` must both be positive.
  // The bucket starts full, so the first `capacity` tokens are available
  // immediately.
  TokenBucket(double tokens_per_second, double capacity);

  TokenBucket(const TokenBucket&) = delete;
  TokenBucket& operator=(const TokenBucket&) = delete;

  // Blocks until `n` tokens are available, then consumes them. `n` must be
  // positive and must not exceed capacity(); a larger request can never be
  // satisfied and would block forever. May block unrelated callers' wakeups
  // only briefly; the internal lock is not held while waiting.
  void Acquire(double n = 1.0);

  // Consumes `n` tokens and returns true if they are available now;
  // otherwise consumes nothing and returns false. Never blocks. `n` must be
  // positive; requests larger than capacity() always fail.
  bool TryAcquire(double n = 1.0);

  double capacity() const { return capacity_; }

 private:
  // Adds tokens accrued since `last_refill_` up to `now`, capping the total
  // at `capacity_`. Requires `mu_` to be held.
  void RefillLocked(std::chrono::steady_clock::time_point now);

  const double rate_;      // Refill rate in tokens per second.
  const double capacity_;  // Maximum number of tokens the bucket can hold.

  std::mutex mu_;
  std::condition_variable cv_;

  // Tokens currently available, in [0, capacity_]. Guarded by mu_.
  double tokens_;
  // When `tokens_` was last brought up to date. Guarded by mu_.
  std::chrono::steady_clock::time_point last_refill_;
};

#endif  // RATE_LIMITER_H_
