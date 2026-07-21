"""Strict-mode behavior tests."""
from __future__ import annotations

import pytest

from exceptions import (
    DuplicateKeyError,
    ParseError,
    UnknownDirectiveError,
)
from exceptions import SyntaxError as ParserSyntaxError
from parser import parse


def test_strict_kwarg_is_accepted():
    parse("a=1", strict=True)


def test_strict_default_is_false():
    text = "@unknown x\nnot valid line\na=1\na=2"
    assert parse(text) == {"a": "2"}


def test_strict_false_explicit_matches_default():
    text = "@unknown x\nnot valid line\na=1\na=2"
    assert parse(text, strict=False) == {"a": "2"}


def test_strict_valid_input_returns_expected_dict():
    assert parse("a=1\nb=2", strict=True) == {"a": "1", "b": "2"}


def test_strict_raises_duplicate_key_error_specifically():
    with pytest.raises(DuplicateKeyError):
        parse("a=1\na=2", strict=True)


def test_strict_raises_unknown_directive_error_specifically():
    with pytest.raises(UnknownDirectiveError):
        parse("@wat foo", strict=True)


def test_strict_raises_syntax_error_specifically():
    with pytest.raises(ParserSyntaxError):
        parse("not a valid line", strict=True)


def test_strict_errors_have_distinct_specific_types():
    with pytest.raises(ParseError) as dup:
        parse("a=1\na=2", strict=True)
    assert isinstance(dup.value, DuplicateKeyError)
    assert not isinstance(dup.value, UnknownDirectiveError)
    assert not isinstance(dup.value, ParserSyntaxError)

    with pytest.raises(ParseError) as unk:
        parse("@wat foo", strict=True)
    assert isinstance(unk.value, UnknownDirectiveError)
    assert not isinstance(unk.value, DuplicateKeyError)
    assert not isinstance(unk.value, ParserSyntaxError)
