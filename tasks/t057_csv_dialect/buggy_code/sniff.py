def sniff_delimiter(text):
    return ","


def parse(text, delimiter=","):
    return [line.split(delimiter) for line in text.splitlines() if line]
