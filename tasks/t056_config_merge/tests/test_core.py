from merge import merge


def test_scalar_replace():
    assert merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_disjoint_keys():
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_nested_dict_value():
    a = {"db": {"host": "h", "port": 5432}}
    b = {"db": {"port": 6000}}
    assert merge(a, b) == {"db": {"host": "h", "port": 6000}}
