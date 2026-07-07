from labelcheck import is_allowed_label


def test_plain_latin_allowed():
    assert is_allowed_label("paypal") is True


def test_latin_with_neutral_chars_allowed():
    assert is_allowed_label("hello-world") is True
    assert is_allowed_label("user_2024") is True


def test_empty_rejected():
    assert is_allowed_label("") is False


def test_japanese_single_script_allowed():
    assert is_allowed_label("日本語ユーザー") is True
