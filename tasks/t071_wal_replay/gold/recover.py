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
    committed = set()
    for rec in records:
        if rec[0] == "commit":
            committed.add(rec[1])
    state = {}
    for rec in records:
        if rec[0] == "set" and rec[1] in committed:
            state[rec[2]] = rec[3]
    return state
