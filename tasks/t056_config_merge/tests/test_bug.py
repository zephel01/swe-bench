from merge import merge


def test_nested_lists_concatenated():
    a = {"x": {"items": [1, 2]}}
    b = {"x": {"items": [3, 4]}}
    assert merge(a, b) == {"x": {"items": [1, 2, 3, 4]}}


def test_does_not_mutate_inputs():
    a = {"x": {"k": 1}, "ys": [1]}
    b = {"x": {"j": 2}, "ys": [2]}
    merge(a, b)
    assert a == {"x": {"k": 1}, "ys": [1]}   # original unchanged
    assert b == {"x": {"j": 2}, "ys": [2]}


def test_bidirectional_type_collision():
    assert merge({"x": 5}, {"x": {"a": 1}}) == {"x": {"a": 1}}
    assert merge({"x": {"a": 1}}, {"x": 5}) == {"x": 5}
