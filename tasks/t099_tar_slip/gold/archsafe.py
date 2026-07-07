import os


def safe_member_path(dest, name):
    # Archive member names use "/"; also defend against "\" so backslash
    # traversal cannot survive to a later Windows-style consumer.
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
        return None
    dest_abs = os.path.abspath(dest)
    target = os.path.abspath(os.path.join(dest_abs, name))
    # Compare against dest plus a separator so that a sibling directory sharing
    # a textual prefix ("/tmp/extract_evil" vs "/tmp/extract") is rejected.
    if target == dest_abs or target.startswith(dest_abs + os.sep):
        return target
    return None
