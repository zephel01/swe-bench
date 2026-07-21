"""Behavioural characterisation tests that hold in every implementation."""
from __future__ import annotations

from norm import normalize_body
from quote import add_quote_level
from render import render


def test_render_plain_text_substitution() -> None:
    assert render("Hi {{name}}!", {"name": "Bob"}) == "Hi Bob!"


def test_render_missing_key_becomes_empty_string() -> None:
    assert render("Hello {{who}}", {}) == "Hello "


def test_render_ampersand_in_value_is_escaped() -> None:
    assert render("Hi {{name}}", {"name": "A&B"}) == "Hi A&amp;B"


def test_quote_prefixes_ordinary_lines() -> None:
    assert add_quote_level("hello\nworld") == "> hello\n> world"


def test_quote_nests_existing_quotes() -> None:
    assert add_quote_level("> quoted\n>> deep") == ">> quoted\n>>> deep"


def test_normalize_strips_trailing_spaces_on_lf_body() -> None:
    assert normalize_body("foo   \nbar\t\n") == "foo\nbar\n"


def test_normalize_adds_missing_trailing_newline() -> None:
    assert normalize_body("hello") == "hello\n"


def test_normalize_leaves_empty_input_empty() -> None:
    assert normalize_body("") == ""
