"""Cross-file type-signature agreement."""
from __future__ import annotations

import typing
from typing import get_type_hints


def test_user_id_annotation_is_str():
    from model import User
    assert get_type_hints(User).get("id") is str


def test_repo_save_takes_user():
    from model import User
    from repo import UserRepo
    hints = get_type_hints(UserRepo.save)
    assert hints.get("user") is User


def test_repo_lookup_methods_take_str_id():
    from repo import UserRepo
    for name in ("get", "exists"):
        hints = get_type_hints(getattr(UserRepo, name))
        assert hints.get("id") is str, f"UserRepo.{name} id must be str"


def test_service_methods_take_str_id():
    from service import UserService
    for name in ("register", "find", "is_registered"):
        hints = get_type_hints(getattr(UserService, name))
        assert hints.get("id") is str, f"UserService.{name} id must be str"


def test_api_get_accepts_int_or_str():
    from api import API
    hints = get_type_hints(API.get)
    id_type = hints.get("id")
    assert id_type is not None, "API.get must annotate id"
    assert set(typing.get_args(id_type)) == {int, str}


def test_public_symbols_present():
    from api import API, make_api
    from model import User
    from repo import UserRepo
    from service import UserService
    assert callable(make_api)
    assert isinstance(User, type)
    assert isinstance(UserRepo, type)
    assert isinstance(UserService, type)
    assert isinstance(API, type)
