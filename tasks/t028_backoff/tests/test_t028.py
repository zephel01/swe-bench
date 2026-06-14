import pytest

from backoff import backoff_schedule


def test_full_jitter_caps():
    out = backoff_schedule(2, 20, 6, "full")
    assert out == [(0, 2), (0, 4), (0, 8), (0, 16), (0, 20), (0, 20)]


def test_equal_jitter_bounds():
    out = backoff_schedule(2, 20, 4, "equal")
    assert out == [(1, 2), (2, 4), (4, 8), (8, 16)]


def test_first_attempt_is_base():
    assert backoff_schedule(1, 100, 1, "full") == [(0, 1)]


def test_validation():
    with pytest.raises(ValueError):
        backoff_schedule(2, 20, 0)
    with pytest.raises(ValueError):
        backoff_schedule(0, 20, 3)
    with pytest.raises(ValueError):
        backoff_schedule(5, 3, 3)
    with pytest.raises(ValueError):
        backoff_schedule(2, 20, 3, "weird")
