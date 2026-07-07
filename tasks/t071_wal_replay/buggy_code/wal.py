"""A minimal write-ahead log.

Records are appended together with a checksum. A torn write (a partial trailing
record left behind by a crash) is detected on read: iteration stops at the first
record whose checksum does not match, so anything at or after a corrupt record
is treated as absent.
"""


def checksum(payload):
    total = 0
    for ch in repr(payload):
        total = (total * 31 + ord(ch)) & 0xFFFFFFFF
    return total


class Wal:
    def __init__(self):
        self._entries = []   # list of [payload, checksum]

    def append(self, payload):
        self._entries.append([payload, checksum(payload)])

    def corrupt_last(self):
        """Simulate a torn trailing write by flipping a checksum bit."""
        if self._entries:
            self._entries[-1][1] ^= 0x1

    def read_valid(self):
        result = []
        for payload, stored in self._entries:
            if checksum(payload) != stored:
                break
            result.append(payload)
        return result
