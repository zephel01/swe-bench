import threading

from buffer import BoundedBuffer

# Deterministic "stolen wakeup" reproduction.
#
# We replace the buffer's condition variable with a wrapper that counts how many
# threads are actually parked inside wait(). Once BOTH consumers are provably
# waiting, the producer adds exactly one item and calls notify_all. If get()
# re-checks its predicate (while) only one consumer takes the item and the other
# goes back to sleep. If get() uses a bare `if`, both consumers proceed past the
# check and the second one pops from an empty list -> IndexError.


class InstrCond:
    def __init__(self, on_wait_count):
        self._c = threading.Condition()
        self._on_wait_count = on_wait_count
        self.waiting = 0

    def __enter__(self):
        return self._c.__enter__()

    def __exit__(self, *exc):
        return self._c.__exit__(*exc)

    def wait(self, timeout=None):
        self.waiting += 1
        self._on_wait_count(self.waiting)
        try:
            return self._c.wait(timeout)
        finally:
            self.waiting -= 1

    def notify(self, n=1):
        return self._c.notify(n)

    def notify_all(self):
        return self._c.notify_all()


def test_stolen_wakeup_does_not_crash_consumer():
    buf = BoundedBuffer(4)

    both_waiting = threading.Event()

    def on_wait_count(n):
        if n >= 2:
            both_waiting.set()

    buf.cond = InstrCond(on_wait_count)

    results = []
    errors = []

    def consumer():
        try:
            results.append(buf.get())
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    c1 = threading.Thread(target=consumer, daemon=True)
    c2 = threading.Thread(target=consumer, daemon=True)
    c1.start()
    c2.start()

    assert both_waiting.wait(5.0), "consumers never both parked in wait()"

    # Exactly one item for two waiting consumers.
    buf.put(42)

    c1.join(timeout=3.0)
    c2.join(timeout=3.0)

    # Release any consumer still (correctly) waiting so the test can clean up.
    buf.put(0)
    c1.join(timeout=3.0)
    c2.join(timeout=3.0)

    assert not errors, f"a woken consumer crashed: {errors}"
    assert 42 in results
