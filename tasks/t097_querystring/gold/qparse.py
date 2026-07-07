import urllib.parse


def parse_query(qs):
    if qs.startswith("?"):
        qs = qs[1:]
    result = {}
    for pair in qs.split("&"):
        if pair == "":
            continue
        if "=" in pair:
            key, value = pair.split("=", 1)
        else:
            key, value = pair, ""
        key = urllib.parse.unquote_plus(key)
        value = urllib.parse.unquote_plus(value)
        result.setdefault(key, []).append(value)
    return result
