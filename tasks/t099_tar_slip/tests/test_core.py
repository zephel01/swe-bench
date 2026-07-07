from archsafe import safe_member_path

DEST = "/tmp/extract"


def test_simple_member():
    assert safe_member_path(DEST, "sub/file.txt") == "/tmp/extract/sub/file.txt"


def test_nested_member():
    assert safe_member_path(DEST, "reports/2024/q1.csv") == (
        "/tmp/extract/reports/2024/q1.csv"
    )


def test_dotted_filename_allowed():
    assert safe_member_path(DEST, "notes..txt") == "/tmp/extract/notes..txt"


def test_plain_traversal_rejected():
    assert safe_member_path(DEST, "../../etc/passwd") is None


def test_absolute_member_rejected():
    assert safe_member_path(DEST, "/etc/passwd") is None
