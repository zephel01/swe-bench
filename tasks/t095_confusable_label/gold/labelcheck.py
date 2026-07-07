import unicodedata

_NEUTRAL = set("-_")
_CJK_SCRIPTS = {"HIRAGANA", "KATAKANA", "CJK"}
_SCRIPT_TOKENS = (
    "LATIN", "CYRILLIC", "GREEK", "HEBREW", "ARABIC",
    "HIRAGANA", "KATAKANA", "CJK", "HANGUL", "THAI",
)


def _script_of(ch):
    # Digits and a couple of neutral separators belong to no single script and
    # never trigger a "mixed script" verdict.
    if ch.isdigit() or ch in _NEUTRAL:
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "UNKNOWN"
    for token in _SCRIPT_TOKENS:
        if token in name:
            return "JAPANESE" if token in _CJK_SCRIPTS else token
    return "OTHER"


def is_allowed_label(label):
    if not label:
        return False
    label = unicodedata.normalize("NFKC", label)
    scripts = set()
    for ch in label:
        script = _script_of(ch)
        if script is not None:
            scripts.add(script)
    return len(scripts) <= 1
