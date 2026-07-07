from render import format_table


def test_uniform_widths():
    out = format_table(["aa", "bb"], [["11", "22"], ["33", "44"]])
    assert out == "aa | bb\n11 | 22\n33 | 44"


def test_single_row():
    out = format_table(["xx", "yy"], [["ab", "cd"]])
    assert out == "xx | yy\nab | cd"
