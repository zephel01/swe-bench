# Bug: counter loses increments under concurrency

Running 8 threads that each call `increment()` 1000 times leaves `value` below
8000: the read-modify-write is not atomic, so updates are lost.

Make `increment` safe under concurrent access (the final total must be exact)
without deadlocking. Single-threaded use already works.
