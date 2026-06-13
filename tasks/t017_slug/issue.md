# Bug: slugify produces invalid URL slugs

`slugify` is supposed to turn arbitrary text into a clean, URL-friendly
slug, but it only handles the simplest case. Real titles contain extra
spaces, punctuation, underscores and mixed case, and the current output
still contains junk. Make it produce tidy slugs (lowercase, words joined
by single hyphens, no leading/trailing or repeated hyphens, no stray
characters).

File: `slug.py`.
