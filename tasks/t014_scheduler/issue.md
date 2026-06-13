# Bug: jobs run in reverse priority order

`Scheduler.run_order()` should return job names with the HIGHEST
priority number first, but it returns the lowest first.
Files: `pq.py` (priority queue) and `scheduler.py` (uses the queue).
The scheduler logic reads correctly — the queue ordering is suspect.
Ties must keep insertion order (FIFO), which currently works and must
not break.
