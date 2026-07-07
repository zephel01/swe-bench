import pytest

from tmplfmt import safe_format


def test_attribute_access_blocked():
    with pytest.raises(ValueError):
        safe_format("{x.__class__}", x=1)


def test_globals_walk_blocked():
    with pytest.raises(ValueError):
        safe_format("{0.__class__.__init__.__globals__}", object())


def test_subscription_blocked():
    with pytest.raises(ValueError):
        safe_format("{conf[secret]}", conf={"secret": "s3cr3t"})


def test_plain_template_not_over_blocked():
    assert safe_format("{greeting}, {0}!", "world", greeting="hi") == "hi, world!"
