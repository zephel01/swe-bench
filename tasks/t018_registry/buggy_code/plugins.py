"""Built-in text plugins (correct — do not change)."""

from registry import register


@register("shout")
def shout(s):
    return s.upper() + "!"


@register("whisper")
def whisper(s):
    return s.lower()
