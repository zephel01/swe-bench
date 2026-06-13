"""Palindrome checking."""


def is_palindrome(text):
    """Return True if text is a palindrome.

    Case, spaces and punctuation are ignored.
    """
    cleaned = "".join(c.lower() for c in text if c.isalnum())
    return cleaned == cleaned[::-1]
