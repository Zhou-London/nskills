// rate_limiter.h
//
// A thread-safe token-bucket rate limiter.
//
// The token-bucket algorithm models a bucket that holds up to `capacity`
// tokens. Tokens are added ("refilled") at a fixed rate of
// `refill_rate_per_sec` tokens per second. Each operation that should be
// rate-limited consumes one or more tokens; when the bucket does not hold
// enough tokens the operation must either wait (Acquire) or fail fast
// (TryAcquire). Because the bucket can accumulate tokens while idle, short
// bursts of up to `capacity` operations are allowed, while the long-term
// average rate is bounded by `refill_rate_per_sec`.

#ifndef RATE_LIMITER_H_
#define RATE_LIMITER_H_

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>

namespace ratelimit {

// TokenBucket implements the token-bucket rate-limiting algorithm.
//
// Thread safety: all public member functions are safe to call concurrently
// from multiple threads. Blocking waiters are woken as tokens become
// available; wake-ups are not guaranteed to be FIFO-fair across waiters.
//
// Example:
//   ratelimit::TokenBucket bucket(/*capacity=*/100,
//                                 /*refill_rate_per_sec=*/50.0);
//   // Blocking use: waits until 10 tokens are available.
//   bucket.Acquire(10);
//   // Non-blocking use: returns immediately.
//   if (bucket.TryAcquire(1)) {
//     // ... permitted to proceed ...
//   } else {
//     // ... rate limit exceeded; shed load or retry later ...
//   }
class TokenBucket {
 public:
  // Constructs a bucket that holds at most `capacity` tokens and refills at
  // `refill_rate_per_sec` tokens per second. The bucket starts full, so up to
  // `capacity` tokens may be acquired immediately after construction.
  //
  // Requirements (checked with assert in debug builds):
  //   - `capacity` must be > 0.
  //   - `refill_rate_per_sec` must be > 0.
  TokenBucket(int64_t capacity, double refill_rate_per_sec);

  // Not copyable or movable: the object owns synchronization primitives and
  // may have threads blocked inside Acquire().
  TokenBucket(const TokenBucket&) = delete;
  TokenBucket& operator=(const TokenBucket&) = delete;

  // Blocks the calling thread until `n` tokens have been acquired, then
  // removes them from the bucket and returns.
  //
  // `n` must be in the range [1, capacity]; requesting more tokens than the
  // bucket can ever hold would block forever, so it is a programming error
  // (checked with assert in debug builds, clamped to capacity in release
  // builds).
  //
  // The wait time is computed from the current token deficit and the refill
  // rate, so waiting threads sleep rather than busy-poll.
  void Acquire(int64_t n);

  // Attempts to acquire `n` tokens without blocking.
  //
  // Returns true and removes `n` tokens from the bucket if at least `n`
  // tokens are currently available; otherwise returns false and leaves the
  // bucket unchanged.
  //
  // `n` must be >= 1. If `n` exceeds `capacity` the call can never succeed
  // and always returns false.
  bool TryAcquire(int64_t n);

  // Returns the number of whole tokens currently available. Intended for
  // monitoring and tests; the value may be stale by the time the caller
  // inspects it, so it must not be used to decide whether an acquire will
  // succeed.
  int64_t AvailableTokens() const;

  // Returns the maximum number of tokens the bucket can hold.
  int64_t capacity() const { return capacity_; }

  // Returns the refill rate in tokens per second.
  double refill_rate_per_sec() const { return refill_rate_per_sec_; }

 private:
  // Monotonic clock used for refill computations; immune to wall-clock
  // adjustments (NTP, manual changes).
  using Clock = std::chrono::steady_clock;

  // Adds tokens accrued since `last_refill_` to `tokens_`, capping the total
  // at `capacity_`, and advances `last_refill_` to `now`.
  //
  // Precondition: `mu_` is held by the caller.
  void RefillLocked(Clock::time_point now);

  const int64_t capacity_;           // Maximum tokens the bucket can hold.
  const double refill_rate_per_sec_; // Tokens added per second.

  mutable std::mutex mu_;  // Guards all mutable state below.

  // Current token balance. Stored as a double so that fractional tokens
  // accrued between refills are not lost to rounding.
  double tokens_;

  // Time at which `tokens_` was last brought up to date.
  Clock::time_point last_refill_;

  // Signaled when tokens are consumed-and-released or when a waiter's
  // computed refill deadline may have passed; blocking Acquire() calls wait
  // on this.
  std::condition_variable cv_;
};

}  // namespace ratelimit

#endif  // RATE_LIMITER_H_
