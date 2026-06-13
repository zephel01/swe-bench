# Bug: LRUCache evicts the most recently used entry

With capacity 2: put(1), put(2), get(1), put(3) — key 2 should be
evicted (least recently used), but key 3 disappears immediately and
key 2 survives. The cache keeps stale entries and drops fresh ones.
