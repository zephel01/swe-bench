"""New-API tests: verify first_name/last_name/property/roundtrip."""
from __future__ import annotations

import json

from storage import load_user, save_user
from user import User


def test_user_exposes_first_name_field():
    u = User(first_name="Alice", last_name="Wonder")
    assert u.first_name == "Alice"


def test_user_exposes_last_name_field():
    u = User(first_name="Alice", last_name="Wonder")
    assert u.last_name == "Wonder"


def test_name_property_concatenates():
    u = User(first_name="Grace", last_name="Hopper")
    assert u.name == "Grace Hopper"


def test_save_writes_new_schema(tmp_path):
    p = tmp_path / "u.json"
    save_user(User(first_name="Alice", last_name="Wonder"), p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("first_name") == "Alice"
    assert data.get("last_name") == "Wonder"
    assert "name" not in data


def test_load_reads_new_schema(tmp_path):
    p = tmp_path / "u.json"
    p.write_text(
        json.dumps({"first_name": "Bob", "last_name": "Marley"}),
        encoding="utf-8",
    )
    u = load_user(p)
    assert u.first_name == "Bob"
    assert u.last_name == "Marley"


def test_roundtrip_new_schema(tmp_path):
    p = tmp_path / "u.json"
    save_user(User(first_name="Ada", last_name="Lovelace"), p)
    reloaded = load_user(p)
    assert reloaded.first_name == "Ada"
    assert reloaded.last_name == "Lovelace"
    assert reloaded.name == "Ada Lovelace"


def test_load_of_legacy_file_yields_new_fields(tmp_path):
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps({"name": "Grace Hopper"}), encoding="utf-8")
    user = load_user(p)
    assert user.first_name == "Grace"
    assert user.last_name == "Hopper"
