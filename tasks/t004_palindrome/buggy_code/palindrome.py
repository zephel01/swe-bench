"""Palindrome checking."""


def is_palindrome(text):
    """Return True if text is a palindrome.

    Case, spaces and punctuation are ignored.
    """
    return text == text[::-1]
