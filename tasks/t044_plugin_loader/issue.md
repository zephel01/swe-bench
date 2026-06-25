# Bug: plugin load order is fragile and cycles are not detected

`resolve_order(registry)` is supposed to return plugins in dependency order
(every dependency before the plugin that needs it). Today:

- A three-level chain `c -> b -> a` can come back with `a` placed *after* `b`,
  so a plugin loads before its dependency.
- A cyclic dependency (`a -> b -> a`) does not raise; it should raise
  `CycleError`.
- The result depends on the order plugins were registered in; it must not.

A simple linear two-node dependency already resolves correctly.
