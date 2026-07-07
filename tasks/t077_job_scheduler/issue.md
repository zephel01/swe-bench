# Recurring jobs run in the wrong order and at the wrong time

We use this module to schedule daily jobs. Two things look wrong in production:

- When several jobs share the same priority, they no longer run in the order
  they were queued. A job added later sometimes runs before one that was added
  earlier at the same priority.
- Daily jobs configured for a non-UTC timezone fire at the wrong wall-clock
  time. For some timezones the next run even lands on the wrong day.

Single-timezone (UTC) scheduling and jobs with distinct priorities look fine.
