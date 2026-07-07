import threading

from cell import ResultCell

# Deterministic double-winner reproduction.
#
# We swap the cell's `_done` flag for an object whose truth test blocks the first
# time each thread evaluates it, until the other thread has also evaluated it.
# Without a lock both threads read _done as False, both fall through, and both
# return True (two winners). With a lock the second thread cannot reach the check
# while the first holds the lock, so the gate times out; the first winner sets
# _done to a plain True and the second thread correctly sees it and returns False.

GATE_TIMEOUT = 0.5


class GatedFlag:
    def __init__(self, value, events):
        self._value = value
        self._events = events  # tid -> Event, set on that thread's first check

    def __bool__(self):
        tid = threading.get_ident()
        ev = self._events.get(tid)
        if ev is not None and not ev.is_set():
            ev.set()
            for other_tid, other_ev in self._events.items():
                if other_tid != tid:
                    other_ev.wait(GATE_TIMEOUT)
        return bool(self._value)


def test_concurrent_set_has_one_winner():
    c = ResultCell()
    events = {}
    c._done = GatedFlag(False, events)

    results = {}

    def worker(name, value):
        events[threading.get_ident()] = threading.Event()
        ready.wait()
        results[name] = c.set(value)

    ready = threading.Barrier(3)
    t1 = threading.Thread(target=worker, args=("a", "A"), daemon=True)
    t2 = threading.Thread(target=worker, args=("b", "B"), daemon=True)
    t1.start()
    t2.start()
    ready.wait()

    t1.join(timeout=3.0)
    t2.join(timeout=3.0)
    assert not t1.is_alive() and not t2.is_alive()

    winners = sum(1 for v in results.values() if v is True)
    assert winners == 1, f"expected exactly one winner, got {winners}: {results}"
    assert c.is_done() is True
    assert c.get() in ("A", "B")
