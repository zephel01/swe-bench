from labelpath import is_valid_label_path


def test_valid_paths():
    assert is_valid_label_path("users.profile.name") is True
    assert is_valid_label_path("a") is True
    assert is_valid_label_path("x_1.y_2") is True


def test_invalid_paths():
    assert is_valid_label_path("a..b") is False
    assert is_valid_label_path(".a") is False
    assert is_valid_label_path("a b") is False
    assert is_valid_label_path("") is False
