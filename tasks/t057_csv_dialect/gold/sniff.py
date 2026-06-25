import csv
import io

_CANDIDATES = [",", ";", "\t"]


def _count_unquoted(line, delim):
    count = 0
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == delim and not in_quotes:
            count += 1
    return count


def sniff_delimiter(text):
    first = text.splitlines()[0] if text else ""
    return max(_CANDIDATES, key=lambda d: _count_unquoted(first, d))


def parse(text, delimiter=None):
    if delimiter is None:
        delimiter = sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return list(reader)
