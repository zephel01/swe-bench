from replay import make_snapshot, rebuild
from store import EventStore


def _ev(i, type_, amount):
    return {"id": i, "type": type_, "amount": amount}


def test_replay_after_snapshot_no_double_count():
    s = EventStore()
    s.append(_ev(1, "deposit", 100))
    s.append(_ev(2, "deposit", 50))
    snap = make_snapshot(s)
    s.append(_ev(3, "withdraw", 30))
    state = rebuild(s, snap)
    assert state["balance"] == 120


def test_projection_idempotent():
    s = EventStore()
    s.append(_ev(1, "deposit", 40))
    s.append(_ev(1, "deposit", 40))
    assert rebuild(s)["balance"] == 40
