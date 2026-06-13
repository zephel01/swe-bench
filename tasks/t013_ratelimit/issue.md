# Bug: SlidingWindowRateLimiter allows max_requests + 1

A limiter built with max_requests=3 allows 4 requests inside the window
before rejecting. The window expiry itself works (old requests are
purged correctly); only the counting condition is off.
