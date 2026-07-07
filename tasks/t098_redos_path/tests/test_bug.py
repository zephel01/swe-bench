import time

from labelpath import is_valid_label_path


def test_no_catastrophic_backtracking():
    # A long run of word chars ending in an invalid character. A backtracking
    # regex takes seconds+; a linear one returns in microseconds.
    evil = "a" * 28 + "!"
    start = time.perf_counter()
    result = is_valid_label_path(evil)
    elapsed = time.perf_counter() - start
    assert result is False
    assert elapsed < 1.0


def test_trailing_dot_rejected():
    assert is_valid_label_path("a.") is False


def test_valid_path_not_over_rejected():
    assert is_valid_label_path("service.users.profile") is True
