import pytest

from container import Container
from scopes import REQUEST, SINGLETON


def test_singleton_is_cached():
    c = Container()
    c.register("svc", object, scope=SINGLETON)
    assert c.resolve("svc") is c.resolve("svc")


def test_request_scope_same_within_request():
    c = Container()
    c.register("svc", object, scope=REQUEST)
    req = {}
    assert c.resolve("svc", req) is c.resolve("svc", req)


def test_request_scope_differs_across_requests():
    c = Container()
    c.register("svc", object, scope=REQUEST)
    assert c.resolve("svc", {}) is not c.resolve("svc", {})


def test_request_scope_needs_context():
    c = Container()
    c.register("svc", object, scope=REQUEST)
    with pytest.raises(RuntimeError):
        c.resolve("svc")
