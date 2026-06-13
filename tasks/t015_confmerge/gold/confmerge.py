"""Configuration merging."""


def merge_config(base, override):
    """Merge override into base and return a new dict.

    Nested dicts are merged recursively; other values are replaced.
    Neither input is mutated.
    """
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
