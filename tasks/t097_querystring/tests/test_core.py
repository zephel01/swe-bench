from qparse import parse_query


def test_simple_pairs():
    assert parse_query("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def test_percent_20_space():
    assert parse_query("q=hello%20world") == {"q": ["hello world"]}


def test_empty_string():
    assert parse_query("") == {}


def test_key_without_value():
    assert parse_query("flag") == {"flag": [""]}


def test_raw_percent_kept_literal():
    assert parse_query("x=100%") == {"x": ["100%"]}
