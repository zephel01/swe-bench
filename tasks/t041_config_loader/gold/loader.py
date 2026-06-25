from defaults import DEFAULTS
from validate import coerce_types, fill_defaults

ENV_PREFIX = "CONFIG_"


def _extract(env):
    out = {}
    for key, value in env.items():
        if key.startswith(ENV_PREFIX):
            out[key[len(ENV_PREFIX):].lower()] = value
    return out


def load_config(env):
    overrides = _extract(env)
    merged = fill_defaults(overrides, DEFAULTS)
    return coerce_types(merged, DEFAULTS)
