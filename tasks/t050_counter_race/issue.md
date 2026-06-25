# Bug: counter loses updates under concurrency

The counter is not safe under concurrent access:

- 8 threads each calling `increment()` 1000 times leave `value` below 8000.
- While threads increment, a reader calling `get_and_reset()` (atomically read
  the value and zero it) loses counts: the running total collected across resets
  plus the final value does not add up to the number of increments.

Every operation (`increment`, `add`, `get_and_reset`, reading `value`) must be
atomic so totals are exact, with no deadlock. Single-threaded use already works.
