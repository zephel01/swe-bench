import threading


class RWLock:
    def __init__(self):
        self._cond = threading.Condition()
        self._readers = 0
        self._writer = False
        self._writers_waiting = 0
        self._read_holds = {}

    def acquire_read(self):
        tid = threading.get_ident()
        with self._cond:
            if self._read_holds.get(tid, 0) > 0:
                self._read_holds[tid] += 1
                self._readers += 1
                return
            while self._writer or self._writers_waiting > 0:
                self._cond.wait()
            self._read_holds[tid] = 1
            self._readers += 1

    def release_read(self):
        tid = threading.get_ident()
        with self._cond:
            self._readers -= 1
            self._read_holds[tid] -= 1
            if self._read_holds[tid] == 0:
                del self._read_holds[tid]
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self):
        with self._cond:
            self._writers_waiting += 1
            while self._writer or self._readers > 0:
                self._cond.wait()
            self._writers_waiting -= 1
            self._writer = True

    def release_write(self):
        with self._cond:
            self._writer = False
            self._cond.notify_all()
