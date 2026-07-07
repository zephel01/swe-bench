from qparse import parse_query


def test_duplicate_keys_accumulate():
    assert parse_query("a=1&a=2") == {"a": ["1", "2"]}


def test_plus_is_space():
    assert parse_query("q=a+b") == {"q": ["a b"]}


def test_percent_2b_is_literal_plus():
    assert parse_query("q=a%2Bb") == {"q": ["a+b"]}


def test_normal_input_not_broken():
    assert parse_query("a=1&b=2") == {"a": ["1"], "b": ["2"]}
