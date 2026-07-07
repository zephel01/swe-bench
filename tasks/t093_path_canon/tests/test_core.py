from canonpath import resolve_subpath

BASE = "/srv/data"


def test_simple_relative_path():
    assert resolve_subpath(BASE, "docs/report.pdf") == "/srv/data/docs/report.pdf"


def test_dot_slash_prefix():
    assert resolve_subpath(BASE, "./notes.txt") == "/srv/data/notes.txt"


def test_filename_with_dots_is_allowed():
    assert resolve_subpath(BASE, "archive..bak/file.txt") == (
        "/srv/data/archive..bak/file.txt"
    )


def test_plain_traversal_is_rejected():
    assert resolve_subpath(BASE, "../../etc/passwd") is None
