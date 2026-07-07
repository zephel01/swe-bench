# Bug: concurrent transfers between two accounts hang under load

We move balances between `Account` objects with `bank.transfer(src, dst, amount)`.
Single-threaded transfers and many transfers that all go the *same* direction are
fine. But as soon as two threads transfer between the **same pair** of accounts in
**opposite directions** at the same time, the program occasionally freezes and
never makes progress — the worker threads stay alive forever and the totals are
never reconciled.

Transfers must stay correct (no money created or destroyed, sufficient-funds
respected) and must never be able to freeze, regardless of how many threads move
money between the same accounts in any direction.
