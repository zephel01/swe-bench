import datetime
import re

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_FIXED = {"today": 0, "tomorrow": 1, "yesterday": -1}


def _try_iso(text):
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _weekday_target(rel, name, base):
    delta = (_WEEKDAYS[name] - base.weekday()) % 7
    if rel == "next" and delta == 0:
        delta = 7
    return base + datetime.timedelta(days=delta)


def _relative(text, base):
    m = re.fullmatch(r"in (\d+) days?", text)
    if m:
        return base + datetime.timedelta(days=int(m.group(1)))
    m = re.fullmatch(r"(\d+) days? ago", text)
    if m:
        return base - datetime.timedelta(days=int(m.group(1)))
    m = re.fullmatch(r"(next|this) (\w+)", text)
    if m and m.group(2) in _WEEKDAYS:
        return _weekday_target(m.group(1), m.group(2), base)
    return None


def parse(text, base):
    t = text.strip().lower()
    iso = _try_iso(t)
    if iso is not None:
        return iso
    if t in _FIXED:
        return base + datetime.timedelta(days=_FIXED[t])
    result = _relative(t, base)
    if result is not None:
        return result
    raise ValueError(f"cannot parse date: {text!r}")
