import threading


class Counter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._value += 1

    def add(self, n):
        with self._lock:
            self._value += n

    def get_and_reset(self):
        with self._lock:
            current = self._value
            self._value = 0
            return current

    @property
    def value(self):
        with self._lock:
            return self._value
