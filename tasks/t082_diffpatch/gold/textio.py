"""Line splitting/joining that preserves trailing-newline information."""


def to_lines(text):
    """Split ``text`` into lines, keeping trailing-newline information.

    ``"a\\nb\\n"`` becomes ``["a", "b", ""]`` so that :func:`from_lines`
    reconstructs the original text exactly.
    """
    return text.split("\n")


def from_lines(lines):
    """Join ``lines`` back into text (inverse of :func:`to_lines`)."""
    return "\n".join(lines)
