from sniff import parse, sniff_delimiter


def test_semicolon_detected():
    text = "a;b;c\n1;2;3\n"
    assert sniff_delimiter(text) == ";"
    assert parse(text) == [["a", "b", "c"], ["1", "2", "3"]]


def test_tab_detected():
    text = "a\tb\n1\t2\n"
    assert parse(text) == [["a", "b"], ["1", "2"]]


def test_quoted_delimiter_not_split():
    text = 'name,note\n"Smith, Jr.",ok\n'
    assert parse(text) == [["name", "note"], ["Smith, Jr.", "ok"]]


def test_quoted_newline():
    text = 'a,b\n"line1\nline2",y\n'
    assert parse(text) == [["a", "b"], ["line1\nline2", "y"]]
