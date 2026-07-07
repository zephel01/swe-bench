# Bug: resource pool occasionally hands the same slot to two callers

`ResourcePool.allocate()` returns a free resource id and marks it in use;
`release(rid)` returns it to the pool. Called from a single thread it behaves
perfectly. Under concurrent `allocate()` calls, though, two callers sometimes
receive the **same** id (a double-booking), and sometimes one caller crashes
while the pool tries to remove an id that another caller already took.

Each free id must be handed to at most one caller. Concurrent `allocate()` calls
must return distinct ids (or `None` when exhausted) and must never raise.
