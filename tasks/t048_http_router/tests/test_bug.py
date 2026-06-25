from router import Router


def test_int_param_converted():
    r = Router()
    r.add("/users/{id:int}", "user")
    handler, params = r.match("/users/42")
    assert handler == "user"
    assert params == {"id": 42}


def test_specific_route_wins_over_wildcard():
    r = Router()
    r.add("/files/{path:*}", "blob")
    r.add("/files/readme", "readme")
    handler, _ = r.match("/files/readme")
    assert handler == "readme"


def test_wildcard_captures_rest():
    r = Router()
    r.add("/files/{path:*}", "blob")
    handler, params = r.match("/files/a/b/c")
    assert handler == "blob"
    assert params == {"path": "a/b/c"}
