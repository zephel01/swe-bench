from merge import merge


def test_lists_concatenated_even_when_nested():
    a = {"x": {"items": [1, 2]}}
    b = {"x": {"items": [3, 4]}}
    assert merge(a, b) == {"x": {"items": [1, 2, 3, 4]}}


def test_dict_over_scalar_replaces():
    assert merge({"x": 5}, {"x": {"a": 1}}) == {"x": {"a": 1}}


def test_scalar_over_dict_replaces():
    assert merge({"x": {"a": 1}}, {"x": 5}) == {"x": 5}


def test_none_explicitly_overrides():
    assert merge({"a": 1}, {"a": None}) == {"a": None}


def test_three_levels():
    a = {"l1": {"l2": {"keep": 1, "tags": ["a"]}}}
    b = {"l1": {"l2": {"tags": ["b"], "extra": 9}}}
    assert merge(a, b) == {"l1": {"l2": {"keep": 1, "tags": ["a", "b"], "extra": 9}}}
