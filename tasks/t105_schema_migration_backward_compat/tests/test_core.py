"""Legacy-callsite tests: pass on both buggy (legacy-only) and gold."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from storage import load_user, save_user

LEGACY_NAMES = ["Alice Wonder", "Grace Hopper", "Ada Lovelace", "Marie Curie"]


def _write_legacy(path: Path, name: str) -> None:
    path.write_text(json.dumps({"name": name}), encoding="utf-8")


@pytest.mark.parametrize("full", LEGACY_NAMES)
def test_legacy_name_loads_and_name_attr_matches(tmp_path, full):
    p = tmp_path / "legacy.json"
    _write_legacy(p, full)
    user = load_user(p)
    assert user.name == full


def test_name_is_string(tmp_path):
    p = tmp_path / "legacy.json"
    _write_legacy(p, "Grace Hopper")
    user = load_user(p)
    assert isinstance(user.name, str)


def test_single_word_legacy_name(tmp_path):
    p = tmp_path / "legacy.json"
    _write_legacy(p, "Cher")
    user = load_user(p)
    assert user.name == "Cher"
