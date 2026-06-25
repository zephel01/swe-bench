from container import Container
from scopes import TRANSIENT


def test_transient_new_each_time():
    c = Container()
    c.register("svc", object, scope=TRANSIENT)
    assert c.resolve("svc") is not c.resolve("svc")
