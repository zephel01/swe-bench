from archsafe import safe_member_path

DEST = "/tmp/extract"


def test_prefix_sibling_escape_rejected():
    assert safe_member_path(DEST, "../extract_evil/secret") is None


def test_backslash_traversal_rejected():
    assert safe_member_path(DEST, "..\\..\\etc\\passwd") is None


def test_legit_member_not_over_rejected():
    assert safe_member_path(DEST, "reports/2024/q1.csv") == (
        "/tmp/extract/reports/2024/q1.csv"
    )
