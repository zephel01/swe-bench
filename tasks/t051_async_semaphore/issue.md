# Bug: failed or cancelled tasks deadlock the async pool

`LimitedPool.run` acquires a semaphore before running a coroutine. If the
coroutine raises **or the task is cancelled**, the slot is never returned, so
after a few such tasks every later `run` blocks forever.

Return the slot on every exit path — normal return, exception, and cancellation
— and never exceed the configured concurrency limit. The normal path works.
