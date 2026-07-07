from canonpath import resolve_subpath

BASE = "/srv/data"


def test_double_encoded_traversal_rejected():
    assert resolve_subpath(BASE, "%252e%252e%252fetc/passwd") is None


def test_backslash_traversal_rejected():
    assert resolve_subpath(BASE, "..\\..\\etc\\passwd") is None


def test_fullwidth_traversal_rejected():
    # Fullwidth full stop (U+FF0E) and solidus (U+FF0F) NFKC-normalize to "../".
    assert resolve_subpath(BASE, "．．／etc/passwd") is None


def test_prefix_sibling_directory_rejected():
    # "/srv/data_backup" shares a textual prefix with "/srv/data".
    assert resolve_subpath(BASE, "../data_backup/x") is None


def test_legitimate_path_not_over_rejected():
    assert resolve_subpath(BASE, "reports/2024/q1.csv") == (
        "/srv/data/reports/2024/q1.csv"
    )
