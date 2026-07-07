from colref import num_to_col
from rangeexp import expand_range


def test_num_to_col_labels():
    assert num_to_col(1) == "A"
    assert num_to_col(26) == "Z"
    assert num_to_col(27) == "AA"


def test_expand_range_is_inclusive():
    assert expand_range("A1:B2") == ["A1", "B1", "A2", "B2"]
