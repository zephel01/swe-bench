"""Runtime evidence of str-unified identifiers."""
from __future__ import annotations

import pytest

from api import make_api
from repo import UserRepo


@pytest.fixture
def api():
    return make_api()


def test_stored_keys_are_str_after_int_input(api):
    api.create({"id": 10, "name": "A", "email": "a@example.com"})
    keys = list(api.service.repo._store.keys())
    assert keys, "nothing was stored"
    assert all(isinstance(k, str) for k in keys)


def test_stored_user_id_is_str_after_int_input(api):
    api.create({"id": 11, "name": "B", "email": "b@example.com"})
    users = list(api.service.repo._store.values())
    assert users, "nothing was stored"
    assert all(isinstance(u.id, str) for u in users)


def test_int_input_retrievable_via_str_key(api):
    api.create({"id": 12, "name": "C", "email": "c@example.com"})
    result = api.get("12")
    assert result is not None
    assert result["name"] == "C"


def test_int_and_str_lookups_return_same_user(api):
    api.create({"id": 13, "name": "D", "email": "d@example.com"})
    via_int = api.get(13)
    via_str = api.get("13")
    assert via_int is not None
    assert via_int == via_str


def test_returned_id_is_str(api):
    result = api.create({"id": 14, "name": "E", "email": "e@example.com"})
    assert isinstance(result["id"], str)


def test_repo_get_rejects_non_str_id():
    r = UserRepo()
    with pytest.raises(TypeError):
        r.get(42)


def test_repo_exists_rejects_non_str_id():
    r = UserRepo()
    with pytest.raises(TypeError):
        r.exists(42)
