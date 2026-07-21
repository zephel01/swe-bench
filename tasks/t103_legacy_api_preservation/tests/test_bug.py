"""New-API tests: ``search(SearchRequest)`` must exist and work.

These tests exercise the new object-oriented entry point.  They fail
against the buggy code (which has no ``SearchRequest`` and no dispatch
for it) and pass against the gold code.
"""
from __future__ import annotations

import warnings
from dataclasses import FrozenInstanceError

import pytest

from api import search
from schema import SearchRequest


def test_new_api_accepts_search_request():
    req = SearchRequest(q="python")
    result = search(req)
    assert isinstance(result, list)
    assert len(result) > 0


def test_new_api_applies_filters_from_request():
    req = SearchRequest(q="python", filters={"category": "book"})
    result = search(req)
    assert result
    assert all(r["category"] == "book" for r in result)


def test_new_api_applies_limit():
    req = SearchRequest(q="", limit=2)
    result = search(req)
    assert len(result) == 2


def test_new_api_applies_offset():
    all_req = SearchRequest(q="")
    all_results = search(all_req)
    off_req = SearchRequest(q="", offset=2)
    off_results = search(off_req)
    assert off_results == all_results[2:]


def test_new_api_does_not_emit_deprecation_warning():
    req = SearchRequest(q="python")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        result = search(req)
    assert isinstance(result, list)


def test_new_api_rejects_positional_filters():
    req = SearchRequest(q="python")
    with pytest.raises(TypeError):
        search(req, {"category": "book"})


def test_search_request_is_frozen():
    req = SearchRequest(q="python")
    with pytest.raises(FrozenInstanceError):
        req.q = "rust"


def test_search_request_default_filters_are_empty_mapping():
    req = SearchRequest(q="python")
    assert dict(req.filters) == {}
