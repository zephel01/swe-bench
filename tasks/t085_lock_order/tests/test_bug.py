import threading

from bank import Account, Bank

# Deterministic deadlock harness.
#
# We wrap each account's lock so that the *first* lock a thread acquires is held
# while it waits (bounded) for the other thread to also hold its first lock.
# For the buggy fixed-address ordering the two threads end up holding one lock
# each and then block forever trying to grab the other -> classic AB/BA deadlock.
# For a correct (globally ordered) implementation both threads request the same
# lock first, so only one can proceed; the gate simply times out and the work
# completes.

GATE_TIMEOUT = 0.5


class GatedLock:
    def __init__(self, events):
        self._lock = threading.Lock()
        self._events = events  # tid -> Event, signalled on that thread's 1st acquire

    def acquire(self, *args, **kwargs):
        acquired = self._lock.acquire(*args, **kwargs)
        tid = threading.get_ident()
        ev = self._events.get(tid)
        if acquired and ev is not None and not ev.is_set():
            ev.set()
            for other_tid, other_ev in self._events.items():
                if other_tid != tid:
                    other_ev.wait(GATE_TIMEOUT)
        return acquired

    def release(self):
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


def test_opposite_direction_transfers_do_not_deadlock():
    a = Account(0, 100)
    b = Account(1, 100)
    bank = Bank()

    events = {}
    gate_a = GatedLock(events)
    gate_b = GatedLock(events)
    a.lock = gate_a
    b.lock = gate_b

    ready = threading.Barrier(3)

    def ab():
        events[threading.get_ident()] = threading.Event()
        ready.wait()
        bank.transfer(a, b, 1)

    def ba():
        events[threading.get_ident()] = threading.Event()
        ready.wait()
        bank.transfer(b, a, 1)

    t1 = threading.Thread(target=ab, daemon=True)
    t2 = threading.Thread(target=ba, daemon=True)
    t1.start()
    t2.start()
    ready.wait()

    t1.join(timeout=1.5)
    t2.join(timeout=1.5)

    assert not t1.is_alive(), "transfer A->B deadlocked"
    assert not t2.is_alive(), "transfer B->A deadlocked"
    assert a.balance + b.balance == 200
