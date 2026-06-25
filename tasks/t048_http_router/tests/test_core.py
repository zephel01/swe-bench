from router import Router


def test_static_route():
    r = Router()
    r.add("/health", "health")
    handler, params = r.match("/health")
    assert handler == "health"
    assert params == {}


def test_no_match():
    r = Router()
    r.add("/health", "health")
    handler, params = r.match("/nope")
    assert handler is None
