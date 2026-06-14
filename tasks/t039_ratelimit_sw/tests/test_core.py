import pytest

from limiter import SlidingWindowRateLimiter


def test_within_limit_allowed():
    rl = SlidingWindowRateLimiter(2, 10)
    assert rl.allow("k", 0) is True
    assert rl.allow("k", 1) is True


def test_keys_independent():
    rl = SlidingWindowRateLimiter(1, 10)
    assert rl.allow("a", 0) is True
    assert rl.allow("b", 0) is True


def test_validation():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(0, 10)
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(2, 0)
