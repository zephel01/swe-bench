import pytest

from ratelimit import SlidingWindowRateLimiter


def test_limit_enforced():
    rl = SlidingWindowRateLimiter(3, 10)
    assert rl.allow(0.0)
    assert rl.allow(1.0)
    assert rl.allow(2.0)
    assert not rl.allow(3.0)


def test_window_expiry():
    rl = SlidingWindowRateLimiter(2, 10)
    assert rl.allow(0.0)
    assert rl.allow(1.0)
    assert not rl.allow(2.0)
    assert rl.allow(11.5)  # 0.0 and 1.0 expired


def test_pending():
    rl = SlidingWindowRateLimiter(5, 10)
    rl.allow(0.0)
    rl.allow(1.0)
    assert rl.pending(2.0) == 2
    assert rl.pending(20.0) == 0


def test_invalid():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(0, 10)
