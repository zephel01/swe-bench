# Bug: changes survive a rollback they should not

Running `begin(); begin(); set("a", 5); commit(); rollback()` leaves `a == 5`,
but `get("a")` should be `None`. Committing the inner transaction and then rolling
back the outer one is expected to discard the write entirely.

Single-level commit/rollback and inner-only rollback already behave correctly.
