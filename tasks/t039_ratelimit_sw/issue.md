# Bug: the rate limiter both over-admits and mishandles the window edge

With `limit=2`, `window=10`:

- Three requests in the window are accepted: `allow("k",0)`, `allow("k",1)` and
  `allow("k",2)` all return `True`, but the third must be `False`.
- An event sitting exactly at the window edge is not released. After requests at
  t=0 and t=1, a request at t=10 should be allowed (the t=0 event is now outside
  the window), yet it is rejected.

Multi-key isolation works. Keep the implementation O(1) amortized (perf test).
