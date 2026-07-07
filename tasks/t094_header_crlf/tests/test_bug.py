import pytest

from headerval import sanitize_header_value


def test_nel_rejected():
    with pytest.raises(ValueError):
        sanitize_header_value("session=abc\x85Set-Cookie: admin=1")


def test_line_separator_rejected():
    with pytest.raises(ValueError):
        sanitize_header_value("session=abc Set-Cookie: admin=1")


def test_vertical_tab_rejected():
    with pytest.raises(ValueError):
        sanitize_header_value("session=abc\x0bSet-Cookie: admin=1")


def test_form_feed_rejected():
    with pytest.raises(ValueError):
        sanitize_header_value("session=abc\x0cSet-Cookie: admin=1")


def test_non_ascii_printable_not_over_rejected():
    assert sanitize_header_value("Bjørn") == "Bjørn"
