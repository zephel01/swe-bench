"""Outer-behaviour tests. These stay green on both buggy and gold builds
and act as regression traps: any "fix" that breaks these has changed
observable behaviour outside the three known symptoms.
"""
from __future__ import annotations

from naming import generation_key, sort_generations
from rotator import rotate
from writer import SizeLimitedWriter


def test_writer_creates_and_appends(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=1024)
    w.write("hello")
    w.write("world")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "hello" in text
    assert "world" in text


def test_writer_size_is_non_negative(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=1024)
    assert w.current_size() == 0
    w.write("abc")
    assert w.current_size() >= 3


def test_writer_reset_clears_state(tmp_path):
    p = tmp_path / "app.log"
    w = SizeLimitedWriter(p, max_bytes=100)
    w.write("data")
    w.reset()
    assert w.current_size() == 0
    assert p.read_text(encoding="utf-8") == ""


def test_rotate_removes_base_and_produces_archive(tmp_path):
    p = tmp_path / "app.log"
    p.write_text("payload\n", encoding="utf-8")
    rotate(p, keep=5)
    assert not p.exists()
    gz_files = list(tmp_path.glob("app.log.*.gz"))
    assert len(gz_files) >= 1


def test_rotate_is_noop_when_missing(tmp_path):
    p = tmp_path / "missing.log"
    rotate(p, keep=3)
    assert not p.exists()
    assert list(tmp_path.iterdir()) == []


def test_generation_key_returns_non_empty_string(tmp_path):
    key = generation_key("app.log.3.gz")
    assert isinstance(key, str)
    assert key


def test_sort_generations_is_stable_for_single_digits(tmp_path):
    names = ["app.log.1.gz", "app.log.2.gz", "app.log.3.gz"]
    result = sort_generations(names)
    assert sorted(result) == sorted(names)
    assert result[0] == "app.log.1.gz"
    assert result[-1] == "app.log.3.gz"
