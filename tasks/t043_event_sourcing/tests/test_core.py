from replay import rebuild
from store import EventStore


def _ev(i, type_, amount):
    return {"id": i, "type": type_, "amount": amount}


def test_rebuild_from_scratch():
    s = EventStore()
    s.append(_ev(1, "deposit", 100))
    s.append(_ev(2, "withdraw", 30))
    s.append(_ev(3, "deposit", 10))
    assert rebuild(s)["balance"] == 80


def test_empty_store():
    assert rebuild(EventStore())["balance"] == 0
