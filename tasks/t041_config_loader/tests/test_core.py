from loader import load_config


def test_defaults_when_no_inputs():
    cfg = load_config({})
    assert cfg["db_port"] == 5432
    assert cfg["db_host"] == "localhost"
    assert cfg["debug"] is False


def test_env_only_override_typed():
    cfg = load_config({"CONFIG_DB_PORT": "6000"})
    assert cfg["db_port"] == 6000
    assert isinstance(cfg["db_port"], int)


def test_unrelated_env_ignored():
    cfg = load_config({"PATH": "/usr/bin"})
    assert cfg["db_port"] == 5432
