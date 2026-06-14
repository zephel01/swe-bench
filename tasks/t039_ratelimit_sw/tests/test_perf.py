from limiter import SlidingWindowRateLimiter


def test_many_calls_complete_quickly():
    # O(n^2) 実装はタスクのperf_timeoutで落ちる。正しい実装はO(1)償却。
    rl = SlidingWindowRateLimiter(100, 1000)
    allowed = 0
    for t in range(100_000):
        if rl.allow("k", t):
            allowed += 1
    assert allowed > 0
