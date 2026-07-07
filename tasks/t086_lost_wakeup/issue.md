# Bug: bounded buffer crashes when several consumers wait for one item

`BoundedBuffer` lets producers `put` and consumers `get`, blocking when empty or
full using a single condition variable. With one producer and one consumer it is
fine. But when several consumers are blocked in `get` on an empty buffer and a
producer adds a single item, one consumer occasionally blows up with an
`IndexError` (popping from an empty buffer) instead of simply going back to
sleep.

Every consumer that is woken must re-verify there is actually something to take
before taking it, so that a single produced item is handed to exactly one
consumer and the others keep waiting. `get` must never raise.
