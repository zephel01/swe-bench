import os


def safe_member_path(dest, name):
    target = os.path.normpath(os.path.join(dest, name))
    if target.startswith(dest):
        return target
    return None
