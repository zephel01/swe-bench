from slug import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_collapse_spaces():
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_specials():
    assert slugify("Special!@# Chars") == "special-chars"


def test_underscores():
    assert slugify("snake_case_name") == "snake-case-name"


def test_trim_and_repeat_hyphens():
    assert slugify("--trim--") == "trim"
    assert slugify("Already-Slug") == "already-slug"


def test_empty_like():
    assert slugify("") == ""
    assert slugify("!!!") == ""
