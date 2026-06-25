import datetime

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def parse(text, base):
    t = text.strip()
    try:
        return datetime.date.fromisoformat(t)
    except ValueError:
        pass
    if t == "today":
        return base
    if t == "tomorrow":
        return base + datetime.timedelta(days=1)
    if t == "yesterday":
        return base - datetime.timedelta(days=1)
    parts = t.split()
    if len(parts) == 2 and parts[1] in _WEEKDAYS:
        delta = (_WEEKDAYS[parts[1]] - base.weekday()) % 7
        return base + datetime.timedelta(days=delta)
    raise ValueError(f"cannot parse date: {text!r}")
