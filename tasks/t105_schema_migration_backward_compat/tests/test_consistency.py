"""Cross-module consistency: migrate_legacy contract and boundary behaviour."""
from __future__ import annotations

import json

import pytest

import migration
from storage import load_user, save_user
from user import User


def test_migrate_legacy_converts_old_schema():
    result = migration.migrate_legacy({"name": "Alice Wonder"})
    assert result == {"first_name": "Alice", "last_name": "Wonder"}


def test_migrate_legacy_single_word():
    result = migration.migrate_legacy({"name": "Cher"})
    assert result == {"first_name": "Cher", "last_name": ""}


def test_migrate_legacy_passthrough_on_new_schema():
    src = {"first_name": "Bob", "last_name": "Marley"}
    result = migration.migrate_legacy(src)
    assert result == src
    assert result is not src  # must be a shallow copy


def test_save_after_legacy_load_emits_new_schema(tmp_path):
    src = tmp_path / "legacy.json"
    src.write_text(json.dumps({"name": "Marie Curie"}), encoding="utf-8")
    user = load_user(src)
    dst = tmp_path / "migrated.json"
    save_user(user, dst)
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert data == {"first_name": "Marie", "last_name": "Curie"}


def test_migrate_legacy_rejects_empty_record():
    with pytest.raises(KeyError):
        migration.migrate_legacy({})


def test_user_has_first_and_last_name_annotations():
    from dataclasses import fields
    field_names = {f.name for f in fields(User)}
    assert {"first_name", "last_name"} <= field_names
