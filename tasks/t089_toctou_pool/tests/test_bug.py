import threading

from pool import ResourcePool

# Deterministic double-allocation reproduction.
#
# We swap the pool's free-list for a list subclass that, the first time a thread
# peeks index 0, holds there until the *other* thread has also peeked. With no
# lock around allocate() both threads read the same head id and then both try to
# remove it: one gets it, the other double-books it or raises ValueError removing
# an id that is already gone. With a proper lock the second thread can't even
# reach the peek while the first holds the lock, so the gate simply times out and
# the two allocations are distinct.

GATE_TIMEOUT = 0.5


class GatedFreeList(list):
    def configure(self, events):
        self._events = events  # tid -> Event, set on that thread's first peek

    def __getitem__(self, index):
        value = super().__getitem__(index)
        events = getattr(self, "_events", None)
        if index == 0 and events is not None:
            tid = threading.get_ident()
            ev = events.get(tid)
            if ev is not None and not ev.is_set():
                ev.set()
                for other_tid, other_ev in events.items():
                    if other_tid != tid:
                        other_ev.wait(GATE_TIMEOUT)
        return value


def test_concurrent_allocate_returns_distinct_ids():
    pool = ResourcePool([100, 101, 102])
    gated = GatedFreeList(pool._free)
    events = {}
    gated.configure(events)
    pool._free = gated

    results = {}
    errors = []

    def worker(name):
        events[threading.get_ident()] = threading.Event()
        ready.wait()
        try:
            results[name] = pool.allocate()
        except Exception as exc:  # noqa: BLE001
            errors.append((name, exc))

    ready = threading.Barrier(3)
    t1 = threading.Thread(target=worker, args=("a",), daemon=True)
    t2 = threading.Thread(target=worker, args=("b",), daemon=True)
    t1.start()
    t2.start()
    ready.wait()

    t1.join(timeout=3.0)
    t2.join(timeout=3.0)
    assert not t1.is_alive() and not t2.is_alive()

    assert not errors, f"allocate() raised: {errors}"
    ids = [results["a"], results["b"]]
    assert None not in ids, f"unexpected exhaustion: {ids}"
    assert len(set(ids)) == 2, f"same id handed out twice: {ids}"
