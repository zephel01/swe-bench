from decode import loads
from encode import dumps


def _roundtrip(record):
    return loads(dumps(record))


def test_pipe_in_value_survives():
    rec = {"path": "a|b|c"}
    assert _roundtrip(rec) == rec


def test_false_boolean_restored():
    rec = {"flag": False}
    assert _roundtrip(rec) == rec
