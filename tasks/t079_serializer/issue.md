# Round-tripping records corrupts some fields

We serialize small records to a single line with `dumps` and read them back
with `loads`. Round-tripping should return an equal record, but:

- Values that contain a pipe character `|` come back split or mangled, and
  sometimes `loads` raises instead of returning the record.
- Boolean fields set to `False` come back as `True` after a round trip.

Records with plain text values and boolean `True` survive fine.
