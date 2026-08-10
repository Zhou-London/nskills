// rate_limiter.h
//
// A thread-safe token-bucket rate limiter.
//
// The token bucket algorithm works as follows:
//   - Tokens are added to a bucket at a fixed rate (refill_rate tokens/sec).
//   - The bucket holds at most `capacity` tokens; excess tokens are discarded,
//     which bounds the maximum burst size.
//   - Each operation consumes some number of tokens. If enough tokens are
//     available the operation proceeds immediately; otherwise the caller may
//     either wait (Acquire) or fail fast (TryAcquire).
//
// Typical usage:
//
//   TokenBucket bucket(/*capacity=*/100.0, /*refill_rate=*/50.0);
//
//   // Blocking: waits until 5 tokens are available.
//   bucket.Acquire(5);
//
//   // Non-blocking: returns false immediately if tokens are insufficient.
//   if (bucket.TryAcquire(5)) {
//     // ... proceed with rate-limited work ...
//   }
//
// Thread safety: all public methods are safe to call concurrently from
// multiple threads.

#ifndef RATE_LIMITER_H_
#define RATE_LIMITER_H_

#include <chrono>
#include <condition_variable>
#include <mutex>

namespace ratelimit {

// A token bucket that refills continuously at a fixed rate.
//
// Tokens are tracked as a floating-point count so that refill can be computed
// lazily and precisely from elapsed time, rather than by a background timer
// thread. There is no internal thread; refill happens on demand inside each
// public method.
class TokenBucket {
 public:
  // Constructs a token bucket.
  //
  // Args:
  //   capacity:     Maximum number of tokens the bucket can hold (> 0).
  //                 This bounds the largest possible burst.
  //   refill_rate:  Tokens added per second (> 0).
  //   initial_tokens: Number of tokens available at construction time.
  //                 Values are clamped to [0, capacity]. Defaults to a full
  //                 bucket (capacity) if negative.
  //
  // Behavior is undefined if capacity <= 0 or refill_rate <= 0
  // (an assertion fires in debug builds).
  TokenBucket(double capacity, double refill_rate,
              double initial_tokens = -1.0);

  // Not copyable or movable: the object owns synchronization primitives and
  // may be referenced by blocked waiters.
  TokenBucket(const TokenBucket&) = delete;
  TokenBucket& operator=(const TokenBucket&) = delete;

  // Blocks the calling thread until `n` tokens have been acquired, then
  // deducts them from the bucket.
  //
  // If `n` exceeds the bucket capacity the request can never be satisfied
  // from a full bucket, so `n` is clamped to the capacity to avoid waiting
  // forever.
  //
  // Waiting threads are served as tokens become available; the wait time is
  // computed from the refill rate, so the thread sleeps rather than spins.
  //
  // Args:
  //   n: Number of tokens to acquire. Must be > 0; values <= 0 return
  //      immediately without consuming anything.
  void Acquire(double n = 1.0);

  // Attempts to acquire `n` tokens without blocking.
  //
  // Args:
  //   n: Number of tokens to acquire. Must be > 0; values <= 0 succeed
  //      trivially without consuming anything.
  //
  // Returns:
  //   true  if `n` tokens were available and have been deducted;
  //   false if there were not enough tokens (bucket state is unchanged).
  bool TryAcquire(double n = 1.0);

  // Returns the number of tokens currently available (after applying any
  // pending refill). Intended for monitoring/diagnostics; the value may be
  // stale by the time the caller uses it.
  double AvailableTokens();

  // Accessors for the (immutable) configuration.
  double capacity() const { return capacity_; }
  double refill_rate() const { return refill_rate_; }

 private:
  using Clock = std::chrono::steady_clock;

  // Adds tokens accrued since `last_refill_` to the bucket, capping at
  // `capacity_`, and advances `last_refill_` to now.
  //
  // REQUIRES: `mu_` is held by the caller.
  void RefillLocked();

  const double capacity_;     // Maximum tokens the bucket can hold.
  const double refill_rate_;  // Tokens added per second.

  std::mutex mu_;                  // Guards the mutable state below.
  std::condition_variable cv_;     // Signaled when tokens may be available.
  double tokens_;                  // Current token count, in [0, capacity_].
  Clock::time_point last_refill_;  // Time of the most recent refill.
};

}  // namespace ratelimit

#endif  // RATE_LIMITER_H_
