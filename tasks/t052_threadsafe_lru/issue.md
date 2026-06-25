# Bug: LRU cache exceeds its capacity and is not thread-safe

`LRUCache(capacity)` lets the number of stored entries grow past `capacity`
(insert one item too many before evicting), and concurrent `get`/`put` from
several threads can leave it in an inconsistent state.

Enforce the capacity exactly (never more than `capacity` entries), evict the
least-recently-used entry first, and make operations safe under concurrent
access. Sequential get/put and LRU ordering already work for the basic case.
