"""Shape/behavior smoke tests. Green on both buggy and gold."""
from __future__ import annotations

import pytest

from api import make_api


@pytest.fixture
def api():
    return make_api()


def test_create_returns_dict(api):
    result = api.create({"id": 1, "name": "Alice", "email": "a@example.com"})
    assert isinstance(result, dict)


def test_create_result_has_expected_keys(api):
    result = api.create({"id": 2, "name": "Bob", "email": "b@example.com"})
    assert set(result.keys()) == {"id", "name", "email"}


def test_create_preserves_name_and_email(api):
    result = api.create({"id": 3, "name": "Carol", "email": "c@example.com"})
    assert result["name"] == "Carol"
    assert result["email"] == "c@example.com"


def test_get_absent_returns_none(api):
    assert api.get(999) is None


def test_get_after_create_returns_user_shape(api):
    api.create({"id": 4, "name": "Dave", "email": "d@example.com"})
    result = api.get(4)
    assert result is not None
    assert result["name"] == "Dave"
    assert result["email"] == "d@example.com"


def test_multiple_users_are_isolated(api):
    api.create({"id": 5, "name": "Eve", "email": "e@example.com"})
    api.create({"id": 6, "name": "Frank", "email": "f@example.com"})
    assert api.get(5)["name"] == "Eve"
    assert api.get(6)["name"] == "Frank"


def test_make_api_returns_independent_instances():
    a = make_api()
    b = make_api()
    a.create({"id": 7, "name": "Grace", "email": "g@example.com"})
    assert b.get(7) is None
