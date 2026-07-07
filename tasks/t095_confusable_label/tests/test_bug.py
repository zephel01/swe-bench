from labelcheck import is_allowed_label


def test_latin_greek_mix_rejected():
    # Two Greek omicrons (U+03BF) hidden among Latin letters.
    assert is_allowed_label("gοοgle") is False


def test_latin_cyrillic_mix_rejected():
    # Trailing Cyrillic dze (U+0455) that looks like a Latin "s".
    assert is_allowed_label("clasѕ") is False


def test_single_script_cyrillic_allowed():
    assert is_allowed_label("привет") is True


def test_fullwidth_latin_normalized_and_allowed():
    assert is_allowed_label("ｐａｙｐａｌ") is True
