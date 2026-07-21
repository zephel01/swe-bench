"""Tests that pin the three independent symptoms described in issue.md.

Every assert here targets one specific symptom directly, so a partial
fix that only patches one of the three modules still leaves several of
these red.
"""
from __future__ import annotations

import gzip
from pathlib import Path

from naming import generation_key, sort_generations
from rotator import rotate
from writer import SizeLimitedWriter


# --- Symptom 1: writer size accounting ---------------------------------


def test_writer_size_after_single_write(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=1000)
    w.write("hello")
    assert w.current_size() == 6


def test_writer_size_matches_bytes_on_disk(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=1000)
    w.write("abc")
    w.write("de")
    assert w.current_size() == p.stat().st_size


def test_writer_rotates_exactly_at_configured_boundary(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=6)
    w.write("hello")
    assert w.should_rotate() is True


# --- Symptom 2: rotator generation shifting ----------------------------


def _read_gz(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


def test_rotate_places_new_content_at_gen1(tmp_path):
    base = tmp_path / "app.log"
    base.write_text("A\n", encoding="utf-8")
    rotate(base, keep=5)
    base.write_text("B\n", encoding="utf-8")
    rotate(base, keep=5)
    g1 = tmp_path / "app.log.1.gz"
    assert g1.exists()
    assert _read_gz(g1) == "B\n"


def test_rotate_preserves_previous_generation(tmp_path):
    base = tmp_path / "app.log"
    base.write_text("first\n", encoding="utf-8")
    rotate(base, keep=5)
    base.write_text("second\n", encoding="utf-8")
    rotate(base, keep=5)
    g1 = tmp_path / "app.log.1.gz"
    g2 = tmp_path / "app.log.2.gz"
    assert g1.exists()
    assert g2.exists()
    assert _read_gz(g1) == "second\n"
    assert _read_gz(g2) == "first\n"


def test_rotate_chain_keeps_all_data(tmp_path):
    base = tmp_path / "app.log"
    contents = ["one\n", "two\n", "three\n"]
    for c in contents:
        base.write_text(c, encoding="utf-8")
        rotate(base, keep=5)
    for i, expected in enumerate(reversed(contents), start=1):
        g = tmp_path / f"app.log.{i}.gz"
        assert g.exists(), f"generation {i} missing"
        assert _read_gz(g) == expected


# --- Symptom 3: numeric ordering of generation keys --------------------


def test_generation_key_orders_ten_after_two(tmp_path):
    key_2 = generation_key("app.log.2.gz")
    key_10 = generation_key("app.log.10.gz")
    assert key_2 < key_10


def test_sort_generations_uses_numeric_order(tmp_path):
    names = [
        "app.log.10.gz",
        "app.log.2.gz",
        "app.log.1.gz",
        "app.log.20.gz",
    ]
    result = sort_generations(names)
    assert result == [
        "app.log.1.gz",
        "app.log.2.gz",
        "app.log.10.gz",
        "app.log.20.gz",
    ]


def test_generation_key_width_is_stable(tmp_path):
    keys = [generation_key(f"app.log.{i}.gz") for i in (1, 5, 10, 99)]
    lengths = {len(k) for k in keys}
    assert len(lengths) == 1
