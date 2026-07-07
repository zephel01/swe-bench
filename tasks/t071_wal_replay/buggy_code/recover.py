"""Recover key/value state from a write-ahead log.

Records are tuples:
    ("begin", txid)
    ("set", txid, key, value)
    ("commit", txid)

Only the writes of transactions that reach a matching commit record may be
applied, in log order. Transactions that were begun but never committed (e.g.
the process crashed) must leave no trace -- even if a *different* transaction
that was interleaved with them committed in the meantime.
"""

from wal import Wal


def recover(source):
    records = source.read_valid() if isinstance(source, Wal) else list(source)
    state = {}
    pending = {}      # txid -> list of (key, value)
    for rec in records:
        kind = rec[0]
        if kind == "begin":
            pending[rec[1]] = []
        elif kind == "set":
            pending.setdefault(rec[1], []).append((rec[2], rec[3]))
        elif kind == "commit":
            for ops in pending.values():
                for key, value in ops:
                    state[key] = value
            pending.clear()
    return state
