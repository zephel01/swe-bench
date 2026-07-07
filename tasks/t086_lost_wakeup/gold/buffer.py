import threading


class BoundedBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = []
        self.cond = threading.Condition()

    def put(self, item):
        with self.cond:
            while len(self._items) >= self.capacity:
                self.cond.wait()
            self._items.append(item)
            self.cond.notify_all()

    def get(self):
        with self.cond:
            while not self._items:
                self.cond.wait()
            item = self._items.pop(0)
            self.cond.notify_all()
            return item
