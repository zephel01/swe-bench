import registry
import plugins  # noqa: F401  (import triggers registration)


def test_lookup_calls_function():
    assert registry.get("shout")("hi") == "HI!"
    assert registry.get("whisper")("HEY") == "hey"


def test_available():
    assert registry.available() == ["shout", "whisper"]


def test_missing():
    assert registry.get("nope") is None
