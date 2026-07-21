"""Baseline tests for existing lenient callers."""
from __future__ import annotations

from parser import parse


def test_parse_returns_dict():
    assert isinstance(parse(""), dict)


def test_parse_empty_input():
    assert parse("") == {}


def test_parse_simple_assignment():
    assert parse("a=1") == {"a": "1"}


def test_parse_multiple_assignments():
    text = "a=1\nb=2\nc=3"
    assert parse(text) == {"a": "1", "b": "2", "c": "3"}


def test_parse_trims_whitespace_around_equals():
    assert parse("  key  =  value  ") == {"key": "value"}


def test_parse_ignores_blank_lines():
    text = "\n\na=1\n\n"
    assert parse(text) == {"a": "1"}


def test_parse_ignores_comment_lines():
    text = "# hello\na=1\n# bye"
    assert parse(text) == {"a": "1"}


def test_parse_duplicate_key_last_wins():
    assert parse("a=1\na=2\na=3") == {"a": "3"}


def test_parse_ignores_unknown_directive():
    assert parse("@wat foo\na=1") == {"a": "1"}


def test_parse_ignores_malformed_line():
    assert parse("not a valid line\na=1") == {"a": "1"}


def test_parse_handles_unset_directive():
    text = "a=1\nb=2\n@unset a"
    assert parse(text) == {"b": "2"}
