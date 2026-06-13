"""Word frequency counting."""

import string


def word_frequencies(text):
    """Count word occurrences in text.

    Counting is case-insensitive and surrounding punctuation is ignored.
    Returns a dict mapping word -> count.
    """
    counts = {}
    for raw in text.split():
        word = raw.strip(string.punctuation).lower()
        if not word:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts
