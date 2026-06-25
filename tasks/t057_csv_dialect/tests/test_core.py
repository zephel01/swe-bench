from sniff import parse


def test_standard_comma_csv():
    text = "a,b,c\n1,2,3\n"
    assert parse(text) == [["a", "b", "c"], ["1", "2", "3"]]
