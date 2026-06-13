from palindrome import is_palindrome


def test_classic():
    assert is_palindrome("A man, a plan, a canal: Panama")


def test_simple():
    assert is_palindrome("racecar")


def test_negative():
    assert not is_palindrome("hello")


def test_empty():
    assert is_palindrome("")
