import pytest

from store import ConflictError, Store


def test_update_version_flow():
    s = Store()
    s.create("a", 1)
    _, v = s.read("a")
    s.update("a", v, 2)
    val, v2 = s.read("a")
    assert val == 2
    assert v2 == v + 1
    with pytest.raises(ConflictError):
        s.update("a", v, 3)          # stale version


def test_commit_all_atomic_success():
    s = Store()
    s.create("x", 1)
    s.create("y", 2)
    _, vx = s.read("x")
    _, vy = s.read("y")
    s.commit_all([("x", vx, 10), ("y", vy, 20)])
    assert s.read("x") == (10, vx + 1)
    assert s.read("y") == (20, vy + 1)
