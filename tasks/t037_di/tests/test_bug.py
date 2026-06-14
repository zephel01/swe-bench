import pytest

from container import Container


def test_singleton_is_cached():
    c = Container()
    c.register("svc", lambda _: object(), singleton=True)
    assert c.resolve("svc") is c.resolve("svc")


def _boom(_):
    raise RuntimeError("factory failed")


def test_failed_resolve_does_not_poison_container():
    c = Container()
    c.register("boom", _boom)
    with pytest.raises(RuntimeError):
        c.resolve("boom")
    # 失敗後も再試行できるべき (resolving状態が残って循環誤検出してはいけない)
    with pytest.raises(RuntimeError):
        c.resolve("boom")


def test_cycle_still_detected():
    c = Container()
    c.register("a", lambda ct: ct.resolve("b"))
    c.register("b", lambda ct: ct.resolve("a"))
    with pytest.raises(ValueError):
        c.resolve("a")
