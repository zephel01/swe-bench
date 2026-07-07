import re

# The nested quantifier in "^(\w+\.?)+$" makes a word char be consumable by
# both the inner "\w+" and the outer "+", so a non-matching tail forces
# exponential backtracking. This unambiguous form runs in linear time and also
# fixes the trailing-dot false positive.
_PATTERN = re.compile(r"^\w+(?:\.\w+)*$")


def is_valid_label_path(s):
    return _PATTERN.match(s) is not None
