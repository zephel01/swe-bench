from csv_line import parse_csv_line


def test_plain():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted_comma():
    assert parse_csv_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_escaped_quote():
    assert parse_csv_line('a,"say ""hi""",b') == ["a", 'say "hi"', "b"]


def test_empty_fields():
    assert parse_csv_line("a,,b") == ["a", "", "b"]


def test_single():
    assert parse_csv_line("abc") == ["abc"]
