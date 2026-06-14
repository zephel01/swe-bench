# Bug: two integer intervals that touch are left separate

After `add(1, 2)` then `add(3, 4)`, `intervals()` returns `[(1, 2), (3, 4)]`.
These hold consecutive integers with nothing in between, so they should be the
single interval `[(1, 4)]`.

Overlapping adds (e.g. `[1,5]` + `[3,8]`) and adds with a real gap (e.g. `[1,2]`
+ `[5,6]`) already behave correctly, as does `remove`.
