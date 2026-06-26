from defaults import DEFAULTS
from validate import coerce_types, fill_layers

ENV_PREFIX = "CONFIG_"


def _extract(env):
    out = {}
    for key, value in env.items():
        if key.startswith(ENV_PREFIX):
            out[key[len(ENV_PREFIX):].lower()] = value
    return out


def load_config(env, file_config=None):
    overrides = _extract(env)
    coerced_env = coerce_types(overrides, DEFAULTS)
    return fill_layers(DEFAULTS, file_config or {}, coerced_env)
