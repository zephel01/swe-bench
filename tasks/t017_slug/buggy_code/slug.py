"""URL slug helper."""


def slugify(text):
    # BUG: naive — only lowercases and swaps single spaces
    return text.lower().replace(" ", "-")
