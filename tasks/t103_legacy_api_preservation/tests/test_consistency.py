"""Cross-cutting consistency tests.

Verify that the public surface, the exception hierarchy, and the return
types are all mutually consistent.  These tests fail on the buggy code
(where the new symbols are missing) and pass on the gold code.
"""
from __future__ import annotations

import warnings
from dataclasses import fields

import api
import schema


def test_search_request_class_is_exposed_in_schema_module():
    assert hasattr(schema, "SearchRequest"), (
        "schema module must expose a SearchRequest class"
    )


def test_search_request_has_expected_fields():
    field_names = {f.name for f in fields(schema.SearchRequest)}
    assert {"q", "filters", "limit", "offset"} <= field_names


def test_legacy_deprecation_warning_class_is_a_deprecation_warning():
    assert hasattr(api, "LegacySearchDeprecated")
    assert issubclass(api.LegacySearchDeprecated, DeprecationWarning)


def test_legacy_call_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        api.search("python", {"category": "book"})
    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), "legacy search() call must emit a DeprecationWarning"


def test_new_api_returns_list_of_dicts():
    req = schema.SearchRequest(q="python")
    result = api.search(req)
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, dict)
        assert "id" in item
