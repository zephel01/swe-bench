from merge import merge


def test_nested_dict_recursive_merge():
    a = {"db": {"host": "localhost", "port": 5432}}
    b = {"db": {"port": 6000}}
    assert merge(a, b) == {"db": {"host": "localhost", "port": 6000}}


def test_lists_concatenated():
    assert merge({"x": [1, 2]}, {"x": [3, 4]}) == {"x": [1, 2, 3, 4]}


def test_scalar_over_dict_replaces():
    assert merge({"x": {"a": 1}}, {"x": 5}) == {"x": 5}
