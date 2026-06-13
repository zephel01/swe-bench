# Bug: clamp() returns the wrong bound

`clamp(-5, 0, 10)` should return 0 (the lower bound) but returns 10.
Values above the upper bound work correctly.
