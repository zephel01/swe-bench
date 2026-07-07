# Bug: WAL recovery applies writes of uncommitted interleaved transactions

`recover()` replays a write-ahead log and should apply only the writes of
transactions that have a matching `commit` record, discarding any transaction
that was begun but never committed (a crash).

This holds for a simple trailing uncommitted transaction. But when transactions
are interleaved, uncommitted writes leak into the recovered state.

Reproduce with this log:
```
("begin", 1)
("set", 1, "x", 1)
("begin", 2)
("set", 2, "y", 2)
("commit", 2)          # only tx2 ever commits
("set", 1, "x", 99)    # tx1 keeps writing, then the process dies
```

Observed: `recover(w)` returns `{"x": 1, "y": 2}`.

Expected: `{"y": 2}` -- tx1 never committed, so `x` must not be present.
Committed data (`y`) and a lone trailing uncommitted transaction are handled
correctly; the leak only appears when an uncommitted transaction is interleaved
with one that commits.
