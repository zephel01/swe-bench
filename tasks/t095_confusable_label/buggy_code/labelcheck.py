_CONFUSABLES = {"а", "е", "о", "р", "с", "х"}  # a few Cyrillic look-alikes


def is_allowed_label(label):
    if not label:
        return False
    for ch in label:
        if ch in _CONFUSABLES:
            return False
    return True
