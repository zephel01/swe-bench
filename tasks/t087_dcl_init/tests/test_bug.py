import threading

from lazy import Lazy

# Deterministic double-init reproduction.
#
# The factory blocks on a Barrier(2) with a small timeout. Two threads call
# get() for the first time. With no locking (or lock without re-check) both
# threads pass the "is None" check and both enter the factory: the barrier gets
# its two parties and releases immediately -> factory runs twice. With proper
# double-checked locking only one thread enters the factory (the other blocks on
# the lock and then sees the value already set); the lone factory call waits out
# the barrier timeout and returns -> factory runs exactly once.

BARRIER_TIMEOUT = 0.5


def test_concurrent_first_use_builds_once():
    creations = []
    creations_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def factory():
        try:
            barrier.wait(timeout=BARRIER_TIMEOUT)
        except threading.BrokenBarrierError:
            pass
        with creations_lock:
            creations.append(1)
        return object()

    lazy = Lazy(factory)
    results = {}

    def caller(name):
        results[name] = lazy.get()

    ready = threading.Barrier(3)

    def worker(name):
        ready.wait()
        caller(name)

    t1 = threading.Thread(target=worker, args=("a",), daemon=True)
    t2 = threading.Thread(target=worker, args=("b",), daemon=True)
    t1.start()
    t2.start()
    ready.wait()

    t1.join(timeout=3.0)
    t2.join(timeout=3.0)
    assert not t1.is_alive() and not t2.is_alive()

    assert len(creations) == 1, f"factory ran {len(creations)} times"
    assert results["a"] is results["b"]
