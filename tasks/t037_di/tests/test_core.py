import pytest

from container import Container


def test_transient_new_each_time():
    c = Container()
    c.register("obj", lambda _: object(), singleton=False)
    assert c.resolve("obj") is not c.resolve("obj")


def test_dependency_resolution():
    c = Container()
    c.register("dep", lambda _: 21)
    c.register("svc", lambda ct: ct.resolve("dep") * 2)
    assert c.resolve("svc") == 42


def test_unregistered_raises():
    with pytest.raises(KeyError):
        Container().resolve("nope")
