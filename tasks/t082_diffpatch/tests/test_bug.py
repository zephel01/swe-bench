from patchlib import context_view


def test_full_trailing_context_window():
    text = "\n".join(f"l{i}" for i in range(10))
    assert context_view(text, 4, 5, 2) == "l2\nl3\nl4\nl5\nl6"


def test_trailing_newline_preserved():
    assert context_view("a\nb\nc\n", 0, 1, 5) == "a\nb\nc\n"
