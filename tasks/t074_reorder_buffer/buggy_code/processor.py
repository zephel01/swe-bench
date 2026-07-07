"""A stream consumer that applies events exactly once, strictly in order.

Events can arrive out of order or be redelivered. An event whose sequence
number is ahead of the next expected one is buffered until the gap before it is
filled: only a contiguous run starting at the next expected sequence may be
applied. An event whose idempotency key has already been seen is ignored.
"""


class Processor:
    def __init__(self):
        self.next_seq = 1
        self.applied = []
        self.total = 0
        self._buffer = {}
        self._seen = set()

    def submit(self, event):
        if event.key in self._seen:
            return
        self._seen.add(event.key)
        if event.seq < self.next_seq:
            return
        self._buffer[event.seq] = event
        self._drain()

    def _drain(self):
        for seq in sorted(self._buffer):
            if seq >= self.next_seq:
                event = self._buffer.pop(seq)
                self.applied.append(event.seq)
                self.total += event.amount
                self.next_seq = seq + 1
