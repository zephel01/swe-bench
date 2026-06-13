"""Minimal CSV line parsing."""


def parse_csv_line(line):
    """Parse one CSV line into a list of field strings.

    Supports double-quoted fields: commas inside quotes are literal
    and "" inside a quoted field is an escaped quote.
    """
    fields = []
    current = []
    in_quotes = False
    i = 0
    while i < len(line):
        char = line[i]
        if in_quotes:
            if char == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    current.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                current.append(char)
        elif char == '"':
            in_quotes = True
        elif char == ",":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
        i += 1
    fields.append("".join(current))
    return fields
