# Bug: a subscriber removed mid-dispatch is still called

If one handler unsubscribes another subscriber while an event is being
dispatched, that just-removed subscriber still gets invoked for the same event.
It should be skipped once it has been unsubscribed.

Plain publishing, priority ordering, and unsubscribing before a publish all work.
