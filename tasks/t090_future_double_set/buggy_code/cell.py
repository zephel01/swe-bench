import threading


class ResultCell:
    def __init__(self):
        self._done = False
        self._value = None
        self._lock = threading.Lock()

    def set(self, value):
        if self._done:
            return False
        self._value = value
        self._done = True
        return True

    def get(self):
        return self._value

    def is_done(self):
        return self._done
