# Bug: cache evicts the wrong entry and is not thread-safe

`LRUCache` is supposed to evict the *least recently used* entry, but it behaves
like a FIFO queue: a `get` (or updating an existing key) does not refresh that
key's recency, so a freshly-read key can be evicted before older untouched ones.
It is also unsafe under concurrent `get`/`put` from multiple threads.

A read or an update must mark the key most-recently-used, eviction must drop the
truly least-recently-used entry, capacity must hold exactly, and operations must
be safe under concurrency. Basic put/get and plain capacity already work.
