# Bug: when one job fails, its siblings are left running

`run_all(tasks)` awaits a batch of already-scheduled asyncio tasks and returns
their results in order. When every task succeeds it works. When one task raises,
`run_all` correctly propagates that exception to the caller — but the other tasks
in the batch are left running in the background instead of being stopped. They
hold their resources open, and test/shutdown code that assumes the batch is fully
settled after `run_all` returns sees leaked, still-pending work.

When a task in the batch fails, the remaining unfinished tasks in that same batch
must be cancelled before the failure is propagated, so nothing from the batch is
left running.
