# Bug: an entry is still returned at the very instant it expires

With `ttl=10`, calling `put("a")` at time 0 and then `get("a")` at time 10
returns the stored value, even though by time 10 the entry's lifetime is over and
it should read as a miss (`None`). A `get` at time 5 correctly returns it.

LRU ordering and capacity eviction are otherwise correct.
