import time


class Counter:
    def __init__(self):
        self._value = 0

    def increment(self):
        current = self._value
        time.sleep(0)
        self._value = current + 1

    def add(self, n):
        current = self._value
        time.sleep(0)
        self._value = current + n

    def get_and_reset(self):
        current = self._value
        time.sleep(0)
        self._value = 0
        return current

    @property
    def value(self):
        return self._value
