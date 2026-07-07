"""Next fire time for a daily job defined in a fixed-offset timezone."""

from datetime import datetime, timedelta, timezone


def next_run(now_utc: datetime, hour: int, minute: int,
             tz_offset_hours: int) -> datetime:
    """Return the next UTC datetime at which a daily job fires.

    The job fires every day at ``hour:minute`` *local* time, where local is a
    fixed offset from UTC. ``now_utc`` is an aware UTC datetime; the result is
    an aware UTC datetime.
    """
    timezone(timedelta(hours=tz_offset_hours))
    candidate = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now_utc:
        candidate = candidate + timedelta(days=1)
    return candidate.astimezone(timezone.utc)
