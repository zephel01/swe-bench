"""Serialize a flat record (str/int/bool/None values) to one line."""


def _escape(text):
    """Escape the backslash and pipe delimiters inside a string value."""
    return text.replace("\\", "\\\\").replace("|", "\\|")


def dumps(record):
    """Serialize ``record`` (a dict) to a single-line string."""
    fields = []
    for key, value in record.items():
        if isinstance(value, bool):
            fields.append(f"{key}=b:{'True' if value else 'False'}")
        elif isinstance(value, int):
            fields.append(f"{key}=i:{value}")
        elif value is None:
            fields.append(f"{key}=n:")
        else:
            fields.append(f"{key}=s:{_escape(str(value))}")
    return "|".join(fields)
