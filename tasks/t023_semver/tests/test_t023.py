import pytest

from semver import compare, parse, sort_versions


def test_release_outranks_prerelease():
    assert compare("1.0.0", "1.0.0-alpha") == 1
    assert compare("1.0.0-alpha", "1.0.0") == -1


def test_prerelease_field_count():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1


def test_numeric_lt_alpha_identifier():
    assert compare("1.0.0-alpha.1", "1.0.0-alpha.beta") == -1


def test_core_numeric_order():
    assert compare("1.2.3", "1.2.10") == -1
    assert compare("1.2.3", "1.2.3") == 0


def test_sort_full_chain():
    out = sort_versions(["1.0.0", "1.0.0-rc.1", "1.0.0-alpha", "1.0.0-beta"])
    assert out == ["1.0.0-alpha", "1.0.0-beta", "1.0.0-rc.1", "1.0.0"]


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse("1.0")
