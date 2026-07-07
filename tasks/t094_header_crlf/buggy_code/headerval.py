def sanitize_header_value(value):
    if "\r\n" in value or "\r" in value or "\n" in value:
        raise ValueError("header value contains a line break")
    return value
