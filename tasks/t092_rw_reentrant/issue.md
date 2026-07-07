# Bug: taking a read lock twice hangs when a writer is waiting

`RWLock` is a writer-preferring read/write lock. Nested read sections in a single
thread are common in our code: a function under `acquire_read()` calls a helper
that also does `acquire_read()` / `release_read()` around the same data. This
works fine when no writer is around. But if another thread is waiting for the
write lock at the moment a thread tries to take the read lock a second time, that
second `acquire_read()` blocks forever: the waiting writer needs the reader to
finish, and the reader is stuck waiting behind the writer it can never get past.

A thread that already holds the read lock must be able to acquire it again without
blocking, even while a writer is waiting, so that nested read sections cannot
deadlock. Writers must still get exclusive access and readers must still exclude
writers.
