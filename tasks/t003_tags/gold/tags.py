"""Tag list helpers."""


def add_tag(tag, tags=None):
    """Append tag to tags and return the list.

    If tags is omitted, a fresh list is used.
    """
    if tags is None:
        tags = []
    tags.append(tag)
    return tags
