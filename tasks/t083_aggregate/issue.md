# Group averages are wrong: some groups merge and means get truncated

`aggregate(rows)` groups rows by their `(g, s)` pair and returns the mean of
each group's `v` values. Two things are wrong in the output:

- Rows that belong to different `(g, s)` groups are sometimes lumped into a
  single group, so their values are averaged together by mistake.
- The averages come back rounded down to whole numbers instead of the true
  fractional mean.

Groups whose keys can't be confused, and groups whose values happen to average
to a whole number, look correct.
