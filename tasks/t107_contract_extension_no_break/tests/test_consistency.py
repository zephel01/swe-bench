"""Consistency: exception hierarchy and signature."""
from __future__ import annotations

import inspect

import exceptions
from exceptions import (
    DuplicateKeyError,
    ParseError,
    UnknownDirectiveError,
)
from exceptions import SyntaxError as ParserSyntaxError
from parser import parse


def test_duplicate_key_error_inherits_parse_error():
    assert issubclass(DuplicateKeyError, ParseError)


def test_unknown_directive_error_inherits_parse_error():
    assert issubclass(UnknownDirectiveError, ParseError)


def test_syntax_error_inherits_parse_error():
    assert issubclass(ParserSyntaxError, ParseError)


def test_specific_errors_are_four_distinct_classes():
    classes = {
        ParseError,
        DuplicateKeyError,
        UnknownDirectiveError,
        ParserSyntaxError,
    }
    assert len(classes) == 4


def test_public_symbols_are_exported_from_exceptions_module():
    for name in (
        "ParseError",
        "DuplicateKeyError",
        "UnknownDirectiveError",
        "SyntaxError",
    ):
        assert hasattr(exceptions, name), f"missing public symbol: {name}"


def test_parse_signature_has_strict_kwarg_defaulting_to_false():
    sig = inspect.signature(parse)
    assert "strict" in sig.parameters, "parse() must accept a 'strict' kwarg"
    assert sig.parameters["strict"].default is False
