import os
import unicodedata
import urllib.parse


def _fully_decode(text):
    # Percent-decoding and compatibility normalization must both happen, and
    # they must be repeated until the string stops changing, so that multiply
    # encoded (%252e -> %2e -> .) or fullwidth (U+FF0E -> .) sequences cannot
    # slip past the traversal check by decoding to "../" only later.
    for _ in range(16):
        decoded = unicodedata.normalize("NFKC", urllib.parse.unquote(text))
        if decoded == text:
            break
        text = decoded
    return text


def resolve_subpath(base, user_path):
    decoded = _fully_decode(user_path)
    decoded = decoded.replace("\\", "/")
    if decoded.startswith("/"):
        return None
    candidate = os.path.normpath(os.path.join(base, decoded))
    base_norm = os.path.normpath(base)
    if candidate == base_norm or candidate.startswith(base_norm + os.sep):
        return candidate
    return None
