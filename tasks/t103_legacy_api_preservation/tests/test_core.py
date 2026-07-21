"""Core contract tests: the legacy ``search(q, filters)`` shape.

These tests must pass against both the buggy (legacy-only) code and the
gold (dual-API) code.  They therefore call the legacy form only, and
suppress any deprecation warnings the gold implementation may emit.
"""
from __future__ import annotations

import warnings

from api import search


def _legacy_search(q, filters=None):
    """Invoke the legacy signature while ignoring deprecation warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if filters is None:
            return search(q)
        return search(q, filters)


def test_legacy_returns_list():
    assert isinstance(_legacy_search("python"), list)


def test_legacy_finds_matching_titles():
    ids = {r["id"] for r in _legacy_search("python")}
    assert 1 in ids
    assert 2 in ids
    assert 4 in ids


def test_legacy_no_match_returns_empty():
    assert _legacy_search("nonexistent-xyz-token") == []


def test_legacy_filters_reduces_results():
    result = _legacy_search("python", {"category": "book"})
    assert result, "expected at least one book result"
    assert all(r["category"] == "book" for r in result)


def test_legacy_empty_filters_equivalent_to_none():
    assert _legacy_search("guide", {}) == _legacy_search("guide")


def test_legacy_case_insensitive_query():
    upper = {r["id"] for r in _legacy_search("PYTHON")}
    lower = {r["id"] for r in _legacy_search("python")}
    assert upper == lower


def test_legacy_filter_by_lang():
    result = _legacy_search("python", {"lang": "ja"})
    assert result
    assert all(r["lang"] == "ja" for r in result)


def test_legacy_multiple_filters_all_applied():
    result = _legacy_search("python", {"category": "book", "lang": "en"})
    for item in result:
        assert item["category"] == "book"
        assert item["lang"] == "en"
