from limiter import SlidingWindowRateLimiter


def test_over_limit_is_blocked():
    rl = SlidingWindowRateLimiter(2, 10)
    assert rl.allow("k", 0) is True
    assert rl.allow("k", 1) is True
    assert rl.allow("k", 2) is False      # 3件目は窓内なので拒否


def test_boundary_event_expires_at_window_edge():
    rl = SlidingWindowRateLimiter(2, 10)
    assert rl.allow("k", 0) is True
    assert rl.allow("k", 1) is True
    assert rl.allow("k", 10) is True      # t=0 はちょうど窓外 → 解放され許可
