# Bug: replaying after a snapshot double-counts events

After `make_snapshot(store)` we append more events and call
`rebuild(store, snapshot)`. The balance comes out too high: events captured by
the snapshot are applied a second time.

A rebuild from a snapshot must only apply events recorded **after** the
snapshot offset, and applying the same event id twice must be a no-op
(idempotent projection). Rebuilding from scratch (no snapshot) already works.
