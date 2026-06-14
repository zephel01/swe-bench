from csvparse import parse_csv


def test_plain_rows():
    assert parse_csv("a,b,c\n1,2,3") == [["a", "b", "c"], ["1", "2", "3"]]


def test_quoted_comma():
    assert parse_csv('"a,b",c') == [["a,b", "c"]]


def test_doubled_quote_escape():
    assert parse_csv('"she said ""hi"""') == [['she said "hi"']]


def test_embedded_newline():
    assert parse_csv('"line1\nline2",x') == [["line1\nline2", "x"]]


def test_crlf_and_empty_fields():
    assert parse_csv("a,,c\r\nx,y,z") == [["a", "", "c"], ["x", "y", "z"]]


def test_trailing_newline_no_phantom_row():
    assert parse_csv("a,b\n") == [["a", "b"]]
