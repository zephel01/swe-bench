def fill_defaults(overrides, defaults):
    merged = dict(defaults)
    merged.update(overrides)
    return merged


def coerce_types(cfg, defaults):
    out = {}
    for key, value in cfg.items():
        if key in defaults and isinstance(value, str):
            target = type(defaults[key])
            if target is bool:
                out[key] = value.strip().lower() in ("1", "true", "yes", "on")
            elif target is int:
                out[key] = int(value)
            elif target is float:
                out[key] = float(value)
            else:
                out[key] = value
        else:
            out[key] = value
    return out
