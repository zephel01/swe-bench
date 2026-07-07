# Bug: out-of-order events are applied across a gap, and the missing one is lost

The `Processor` applies events exactly once, strictly in sequence order. An
event whose `seq` is ahead of `next_seq` must be buffered until the missing
sequence numbers before it have arrived; only a contiguous run starting at
`next_seq` may be applied.

Reproduce:
1. `submit(Event(1, "k1", 10))` -> applied `[1]`, `next_seq == 2`.
2. `submit(Event(3, "k3", 30))` -- sequence 2 has not arrived yet.
3. `submit(Event(2, "k2", 20))`.

Observed:
- After step 2, `applied == [1, 3]` -- sequence 3 was applied even though 2 was
  still missing, and `next_seq` jumped to 4.
- At step 3, sequence 2 is now "in the past" (`2 < next_seq`) and is silently
  dropped, so `applied` stays `[1, 3]` and its amount never counts.

Expected: after step 2, `applied == [1]` (3 buffered); after step 3,
`applied == [1, 2, 3]` with `total == 60`. In-order delivery and duplicate
idempotency-key suppression both work; only out-of-order arrival with a gap
misbehaves.
