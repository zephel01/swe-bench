import pytest

from jsonparse import loads


def test_nested_structure():
    assert loads('{"a":1,"b":[true,false,null]}') == {
        "a": 1, "b": [True, False, None],
    }


def test_unicode_escape():
    assert loads('"\\u0041\\u3042"') == "Aあ"


def test_numbers():
    assert loads("-12.5e2") == -1250.0
    assert loads("42") == 42


def test_whitespace_and_simple_escapes():
    assert loads('  [1, 2, 3]  ') == [1, 2, 3]
    assert loads('"line\\n"') == "line\n"


def test_errors():
    with pytest.raises(ValueError):
        loads("[1,2,]")
    with pytest.raises(ValueError):
        loads("1 2")
