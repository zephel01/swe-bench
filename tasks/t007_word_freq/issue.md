# Bug: word_frequencies() is case-sensitive and keeps punctuation

The docstring promises case-insensitive counting with punctuation stripped,
but `word_frequencies("Dog dog DOG.")` returns three separate keys
(`Dog`, `dog`, `DOG.`) instead of `{"dog": 3}`.
