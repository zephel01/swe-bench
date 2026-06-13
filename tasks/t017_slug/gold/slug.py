"""URL slug helper."""

import re


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")
