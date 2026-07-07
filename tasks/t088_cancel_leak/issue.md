# Bug: cancelling a job corrupts the pool's bookkeeping

`JobRunner.run(name, coro)` tracks how many jobs are in flight (`in_use`) and the
set of currently `active` job names while it awaits the job. Normal completion
and even jobs that raise are accounted for correctly. But when a job is
**cancelled** while it is awaiting, the runner never decrements `in_use` and
never removes the name from `active`. After a few cancellations the runner
believes jobs are still running that are long gone, and its concurrency counter
only ever grows.

Cancellation must be accounted for exactly like normal completion and failure:
`in_use` returns to its prior value and the name leaves `active`, no matter how
the awaited job ends.
