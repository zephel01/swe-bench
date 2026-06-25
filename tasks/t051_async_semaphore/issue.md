# Bug: a failing task deadlocks the async pool

`LimitedPool.run` acquires a semaphore before running a coroutine. If the
coroutine raises, the semaphore is never released, so after a few failures all
further `run` calls block forever.

Release the slot on every path (success or exception) and never exceed the
configured concurrency limit. The normal (no-exception) path already works.
