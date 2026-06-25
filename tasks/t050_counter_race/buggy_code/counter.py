import time


class Counter:
    def __init__(self):
        self._value = 0

    def increment(self):
        current = self._value
        time.sleep(0)
        self._value = current + 1

    @property
    def value(self):
        return self._value
