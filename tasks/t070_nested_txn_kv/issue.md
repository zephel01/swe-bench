# Bug: rolling back an outer transaction keeps a committed child's writes

Our `KVStore` supports nested transactions. `commit()` on a nested transaction
is not supposed to make its writes durable -- it only promotes them into the
enclosing transaction, which can still be rolled back.

Reproduce:
1. `begin()` (parent), `set("a", "A")`.
2. `begin()` (child), `set("b", "B")`, `set("a", "A2")`.
3. `commit()` the child.
4. `rollback()` the parent.

Observed after the parent rollback:
- `get("a")` is `None` (correct -- a was restored).
- `get("b")` is still `"B"`. The key that was introduced only inside the
  committed child survives the parent rollback.

Expected: the parent rollback undoes everything done since the parent opened,
including writes made by nested transactions that had been committed into it,
so `get("b")` is `None`. Non-nested savepoint rollback and outer-commit
persistence both behave correctly; only keys unique to a committed child leak.
