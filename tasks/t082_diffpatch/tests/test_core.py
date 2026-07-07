from patchlib import context_view
from textio import from_lines, to_lines


def test_context_view_change_near_end():
    text = "a\nb\nc"
    assert context_view(text, 2, 3, 5) == "a\nb\nc"


def test_roundtrip_no_trailing_newline():
    assert from_lines(to_lines("x\ny")) == "x\ny"


def test_roundtrip_single_line():
    assert from_lines(to_lines("solo")) == "solo"
