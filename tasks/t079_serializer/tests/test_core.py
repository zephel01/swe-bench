from decode import loads
from encode import dumps


def _roundtrip(record):
    return loads(dumps(record))


def test_plain_values():
    rec = {"name": "alice", "age": 30, "active": True, "note": None}
    assert _roundtrip(rec) == rec


def test_empty_record():
    assert _roundtrip({}) == {}


def test_negative_int():
    assert _roundtrip({"balance": -12}) == {"balance": -12}
