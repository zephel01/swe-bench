# Bug: a failed migration leaves later ones marked as applied

When a migration raises partway through `run()`, migrations that never executed
are still recorded as applied. Re-running then skips them, so they are silently
lost.

Each migration's applied-record must be committed only after its function
succeeds. On failure, stop and leave the remaining migrations unapplied so a
later `run()` resumes from where it stopped. The all-succeed path already runs
in dependency order.
