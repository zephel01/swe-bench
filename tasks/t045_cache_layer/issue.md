# Bug: expired cache entries are occasionally returned

`TTLCache.get` should treat an entry as a miss the moment it reaches its
expiry. With `put("k", "v", ttl=10)` at time 0, a `get` at time 10 still
returns `"v"` (it should be `None`), and an expired entry is never evicted from
the backend.

Evaluate the TTL in exactly one place on the read path and make expiry a hard
miss. Basic put/get before expiry already works. Lookup must stay O(1).
