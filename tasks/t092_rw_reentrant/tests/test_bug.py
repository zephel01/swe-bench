import threading

from rwlock import RWLock

# Deterministic reentrant-read deadlock reproduction.
#
# We wrap the lock's condition so we can tell exactly when the writer has parked
# inside acquire_write() (writer preference is now active). Sequence:
#   1. reader thread takes a read lock.
#   2. writer thread calls acquire_write() and blocks (readers > 0). The wrapped
#      condition signals that a thread is now parked in wait().
#   3. only then does the reader take the read lock a SECOND time.
# A non-reentrant writer-preferring lock makes step 3 block (writers_waiting > 0)
# while the writer waits for readers to hit zero -> deadlock. A reentrant read
# lock lets step 3 proceed immediately; the reader releases both holds, the writer
# gets in, and everyone finishes.


class InstrCond:
    def __init__(self, on_wait):
        self._c = threading.Condition()
        self._on_wait = on_wait

    def __enter__(self):
        return self._c.__enter__()

    def __exit__(self, *exc):
        return self._c.__exit__(*exc)

    def wait(self, timeout=None):
        self._on_wait()
        return self._c.wait(timeout)

    def notify(self, n=1):
        return self._c.notify(n)

    def notify_all(self):
        return self._c.notify_all()


def test_reentrant_read_with_waiting_writer_does_not_deadlock():
    lock = RWLock()
    writer_parked = threading.Event()
    lock._cond = InstrCond(writer_parked.set)

    holds_first_read = threading.Event()
    do_reentrant = threading.Event()
    errors = []

    def reader():
        try:
            lock.acquire_read()
            holds_first_read.set()
            do_reentrant.wait(5.0)
            lock.acquire_read()  # reentrant: deadlocks on the buggy lock
            lock.release_read()
            lock.release_read()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def writer():
        holds_first_read.wait(5.0)
        lock.acquire_write()  # blocks until readers reach zero
        lock.release_write()

    rt = threading.Thread(target=reader, daemon=True)
    wt = threading.Thread(target=writer, daemon=True)
    rt.start()
    assert holds_first_read.wait(5.0), "reader never took the first read lock"
    wt.start()
    assert writer_parked.wait(5.0), "writer never parked waiting for the lock"

    # Now the writer is provably waiting; trigger the reentrant read.
    do_reentrant.set()

    rt.join(timeout=1.5)
    wt.join(timeout=1.5)

    assert not rt.is_alive(), "reentrant read deadlocked while a writer waited"
    assert not wt.is_alive(), "writer never acquired the lock"
    assert not errors, f"unexpected error: {errors}"
