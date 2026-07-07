from colref import col_to_num
from rangeexp import parse_cell


def test_col_to_num_single():
    assert col_to_num("A") == 1


def test_col_to_num_z():
    assert col_to_num("Z") == 26


def test_col_to_num_double():
    assert col_to_num("AA") == 27


def test_parse_cell():
    assert parse_cell("AB12") == ("AB", 12)
