# Filtered pages come back short and mis-ordered

Our list endpoint filters records, sorts them, then returns one page at a
time. Two problems appeared after a refactor (reported by users):

- When a filter is active, a "full" page of results comes back with fewer
  rows than the page size, and rows that should appear are missing entirely.
- When several records share the same sort value, they no longer keep their
  original insertion order — records that were added earlier show up after
  records added later.

Unfiltered listing and records with unique sort values look correct.
