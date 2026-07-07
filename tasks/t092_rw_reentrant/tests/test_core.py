import threading

from rwlock import RWLock


def test_read_then_write_sequential():
    lock = RWLock()
    log = []
    lock.acquire_read()
    log.append("r")
    lock.release_read()
    lock.acquire_write()
    log.append("w")
    lock.release_write()
    assert log == ["r", "w"]


def test_multiple_concurrent_readers():
    lock = RWLock()
    peak = {"n": 0}
    counter = {"n": 0}
    mu = threading.Lock()
    inside = threading.Barrier(4)  # forces all 4 readers to overlap deterministically

    def reader():
        lock.acquire_read()
        with mu:
            counter["n"] += 1
            peak["n"] = max(peak["n"], counter["n"])
        inside.wait(5.0)  # every reader holds a read lock at this point
        with mu:
            counter["n"] -= 1
        lock.release_read()

    threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    assert all(not t.is_alive() for t in threads)
    assert peak["n"] == 4  # readers do not exclude each other


def test_writer_is_exclusive():
    lock = RWLock()
    lock.acquire_write()
    assert lock._writer is True
    assert lock._readers == 0
    lock.release_write()
    assert lock._writer is False
