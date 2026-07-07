from tmplfmt import safe_format


def test_named_fields():
    assert safe_format("{name} is {age}", name="Bob", age=42) == "Bob is 42"


def test_positional_fields():
    assert safe_format("{0}-{1}", "a", "b") == "a-b"


def test_literal_braces():
    assert safe_format("{{literal}}") == "{literal}"


def test_format_spec_and_conversion():
    assert safe_format("{0:>5}", "hi") == "   hi"
    assert safe_format("{0!r}", "hi") == "'hi'"
