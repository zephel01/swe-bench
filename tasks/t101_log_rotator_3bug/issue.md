# Log rotator misbehaves under load

We ship a small logging helper split across three modules (`writer.py`,
`rotator.py`, `naming.py`) that appends messages to a text file, rotates
the file once it grows past a configured byte limit, and stores older
generations as `app.log.<N>.gz`. When a single caller writes one message
and prints, everything looks fine.

Once the system runs against real traffic, three separate reports keep
coming in from different teams:

1. **Rotation never fires at the configured boundary.** Operators
   configure a byte limit and load-test the writer. When the limit is
   hit, `should_rotate()` still returns `False` for one more write. The
   file on disk is already past the configured size by the time a
   rotation eventually happens.

2. **Historical data is lost after rotation.** After two rotations we
   expect the most recent snapshot at `app.log.1.gz` and the previous
   one at `app.log.2.gz`. Instead, `app.log.1.gz` is missing entirely
   and the only surviving generation carries the newest data. The old
   file is gone.

3. **Sorting generations does not order them numerically.** Once we get
   past nine generations, listing them through the shared sort key
   puts `app.log.10.gz` in between `app.log.1.gz` and `app.log.2.gz`.
   The dashboard that pages through history therefore lands on the
   wrong "newest" entry.

A smoke test that does a single write followed by a single rotation
using only single-digit generations does not reproduce any of the three
symptoms.
