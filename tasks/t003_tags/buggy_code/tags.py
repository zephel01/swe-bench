"""Tag list helpers."""


def add_tag(tag, tags=[]):
    """Append tag to tags and return the list.

    If tags is omitted, a fresh list is used.
    """
    tags.append(tag)
    return tags
