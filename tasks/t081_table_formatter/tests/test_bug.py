from render import format_table


def test_columns_align_when_header_is_widest():
    out = format_table(["id", "description", "x"],
                       [["1", "a", "9"], ["2", "bb", "8"]])
    lines = out.split("\n")
    assert len({len(ln) for ln in lines}) == 1


def test_no_trailing_whitespace():
    out = format_table(["k", "v"], [["a", "x"], ["bb", "yyyy"]])
    for ln in out.split("\n"):
        assert ln == ln.rstrip()
