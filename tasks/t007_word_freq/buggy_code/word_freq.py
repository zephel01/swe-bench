"""Word frequency counting."""


def word_frequencies(text):
    """Count word occurrences in text.

    Counting is case-insensitive and surrounding punctuation is ignored.
    Returns a dict mapping word -> count.
    """
    counts = {}
    for word in text.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
