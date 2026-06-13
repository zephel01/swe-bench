from tags import add_tag


def test_no_leak():
    assert add_tag("a") == ["a"]
    assert add_tag("b") == ["b"]


def test_explicit_list():
    base = ["x"]
    assert add_tag("y", base) == ["x", "y"]
    assert base == ["x", "y"]
