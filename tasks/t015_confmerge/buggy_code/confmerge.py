"""Configuration merging."""


def merge_config(base, override):
    """Merge override into base and return a new dict.

    Nested dicts are merged recursively; other values are replaced.
    Neither input is mutated.
    """
    result = dict(base)
    result.update(override)
    return result
