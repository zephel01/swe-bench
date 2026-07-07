import string

_FORMATTER = string.Formatter()


def safe_format(template, *args, **kwargs):
    out = []
    for literal, field_name, format_spec, conversion in _FORMATTER.parse(template):
        out.append(literal)
        if field_name is None:
            continue
        # Only a bare argument reference is allowed. Attribute access
        # ("{x.attr}") and subscription ("{x[key]}") can walk to __globals__ and
        # other internals, and a nested field in the format spec ("{x:{y}}")
        # would re-open the same door.
        if "." in field_name or "[" in field_name:
            raise ValueError("attribute or index access is not allowed")
        if format_spec and "{" in format_spec:
            raise ValueError("nested fields are not allowed")
        value, _ = _FORMATTER.get_field(field_name, args, kwargs)
        value = _FORMATTER.convert_field(value, conversion)
        out.append(format(value, format_spec or ""))
    return "".join(out)
