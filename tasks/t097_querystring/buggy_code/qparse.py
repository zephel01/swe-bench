def parse_query(qs):
    result = {}
    for pair in qs.split("&"):
        if not pair:
            continue
        key, _, value = pair.partition("=")
        value = value.replace("%20", " ")
        result[key] = [value]
    return result
