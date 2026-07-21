"""Regression tests that specifically detect the three known defects."""
from __future__ import annotations

from norm import normalize_body
from quote import add_quote_level
from render import render


# --- Bug A: template markup must survive the {{ }} expansion --------------

def test_bug_render_preserves_literal_html_tags() -> None:
    assert render("<p>Hello {{name}}</p>", {"name": "Bob"}) == "<p>Hello Bob</p>"


def test_bug_render_escapes_only_the_value_not_the_template() -> None:
    assert render("<b>{{msg}}</b>", {"msg": "A<B"}) == "<b>A&lt;B</b>"


def test_bug_render_ampersand_inside_template_stays_literal() -> None:
    template = '<a href="?x=1&y=2">{{label}}</a>'
    assert render(template, {"label": "OK"}) == '<a href="?x=1&y=2">OK</a>'


# --- Bug B: empty lines must be requoted with a bare ``>`` marker ---------

def test_bug_quote_preserves_empty_line_as_bare_marker() -> None:
    assert add_quote_level("hi\n\nworld") == "> hi\n>\n> world"


def test_bug_quote_nested_reply_keeps_paragraph_break() -> None:
    assert add_quote_level("> old\n\n> reply") == ">> old\n>\n>> reply"


def test_bug_quote_multiple_consecutive_empty_lines_all_quoted() -> None:
    assert add_quote_level("a\n\n\nb") == "> a\n>\n>\n> b"


# --- Bug C: mixed-CR bodies must fully normalise to LF --------------------

def test_bug_normalize_lone_cr_between_two_lines() -> None:
    assert normalize_body("a\rb") == "a\nb\n"


def test_bug_normalize_multiple_lone_crs_classic_mac() -> None:
    assert normalize_body("one\rtwo\rthree") == "one\ntwo\nthree\n"


def test_bug_normalize_mixed_crlf_and_lone_cr() -> None:
    assert normalize_body("a\r\nb\rc") == "a\nb\nc\n"
