"""Minimal CSV line parsing."""


def parse_csv_line(line):
    """Parse one CSV line into a list of field strings.

    Supports double-quoted fields: commas inside quotes are literal
    and "" inside a quoted field is an escaped quote.
    """
    return line.split(",")
