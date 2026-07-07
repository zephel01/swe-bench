import os
import urllib.parse


def resolve_subpath(base, user_path):
    decoded = urllib.parse.unquote(user_path)
    candidate = os.path.normpath(os.path.join(base, decoded))
    base_norm = os.path.normpath(base)
    if candidate.startswith(base_norm):
        return candidate
    return None
