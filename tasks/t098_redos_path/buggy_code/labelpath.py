import re

_PATTERN = re.compile(r"^(\w+\.?)+$")


def is_valid_label_path(s):
    return _PATTERN.match(s) is not None
