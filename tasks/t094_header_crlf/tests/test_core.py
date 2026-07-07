import pytest

from headerval import sanitize_header_value


def test_plain_value_accepted():
    v = "application/json; charset=utf-8"
    assert sanitize_header_value(v) == v


def test_user_agent_accepted():
    v = "Mozilla/5.0 (X11; Linux x86_64)"
    assert sanitize_header_value(v) == v


def test_horizontal_tab_allowed():
    assert sanitize_header_value("a\tb") == "a\tb"


def test_crlf_rejected():
    with pytest.raises(ValueError):
        sanitize_header_value("a\r\nSet-Cookie: x=1")
