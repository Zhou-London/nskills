#ifndef RATE_LIMITER_H_
#define RATE_LIMITER_H_

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>

namespace ratelimit {

// Token-bucket rate limiter: tokens accrue continuously at a fixed rate up to
// a burst capacity, and each acquisition spends tokens. Thread-safe; all
// methods may be called concurrently from any thread.
class TokenBucket {
 public:
  // Creates a bucket that refills at `tokens_per_second` (must be > 0) up to
  // `capacity` tokens (must be > 0). The bucket starts full, so an initial
  // burst of up to `capacity` tokens succeeds immediately.
  TokenBucket(double tokens_per_second, double capacity);

  TokenBucket(const TokenBucket&) = delete;
  TokenBucket& operator=(const TokenBucket&) = delete;

  // Blocks until `n` tokens are available, then consumes them. `n` must not
  // exceed the bucket capacity, or the call can never be satisfied.
  void Acquire(double n = 1.0);

  // Consumes `n` tokens and returns true if they are available now; otherwise
  // returns false without consuming anything or blocking.
  bool TryAcquire(double n = 1.0);

 private:
  using Clock = std::chrono::steady_clock;

  // Credits tokens accrued since `last_refill_`. Caller must hold `mu_`.
  void RefillLocked(Clock::time_point now);

  const double rate_;      // Refill rate in tokens per second.
  const double capacity_;  // Maximum token balance (burst size).

  std::mutex mu_;
  std::condition_variable cv_;
  double tokens_;                  // Current balance; guarded by mu_.
  Clock::time_point last_refill_;  // Guarded by mu_.
};

}  // namespace ratelimit

#endif  // RATE_LIMITER_H_
