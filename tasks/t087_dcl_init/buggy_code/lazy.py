import threading


class Lazy:
    def __init__(self, factory):
        self._factory = factory
        self._value = None
        self._lock = threading.Lock()

    def get(self):
        if self._value is None:
            self._value = self._factory()
        return self._value
