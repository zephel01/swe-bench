"""Default application configuration."""

DEFAULT_CONFIG = {
    "db": {
        "host": "localhost",
        "port": 5432,
        "options": {"timeout": 30, "ssl": False},
    },
    "log": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "debug": False,
}
