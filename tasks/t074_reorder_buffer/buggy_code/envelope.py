"""Event envelopes for an ordered, idempotent stream consumer.

Each event carries a strictly increasing sequence number and an idempotency
key. The key lets a redelivered event be recognised and dropped; the sequence
number defines the one true order in which events take effect.
"""


class Event:
    __slots__ = ("seq", "key", "amount")

    def __init__(self, seq, key, amount):
        if seq < 1:
            raise ValueError("seq must be >= 1")
        self.seq = seq
        self.key = key
        self.amount = amount
