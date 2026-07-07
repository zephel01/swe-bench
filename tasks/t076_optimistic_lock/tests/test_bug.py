import pytest

from store import ConflictError, Store


def test_commit_all_is_atomic_on_conflict():
    s = Store()
    s.create("x", 1)
    s.create("y", 2)
    _, vx = s.read("x")
    _, vy = s.read("y")

    # A concurrent writer bumps y, making the caller's cached vy stale.
    s.update("y", vy, 99)

    with pytest.raises(ConflictError):
        s.commit_all([("x", vx, 10), ("y", vy, 20)])

    # Atomicity: because y was stale, x must be left completely untouched.
    assert s.read("x") == (1, vx)
    assert s.read("y") == (99, vy + 1)


def test_commit_all_conflict_on_later_key_does_not_bump_earlier():
    s = Store()
    s.create("a", "a0")
    s.create("b", "b0")
    s.create("c", "c0")
    _, va = s.read("a")
    _, vb = s.read("b")
    _, vc = s.read("c")

    s.update("c", vc, "c1")          # c now stale for the caller

    with pytest.raises(ConflictError):
        s.commit_all([("a", va, "a1"), ("b", vb, "b1"), ("c", vc, "c1")])

    # None of a, b may have been written or version-bumped.
    assert s.read("a") == ("a0", va)
    assert s.read("b") == ("b0", vb)
