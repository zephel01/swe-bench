from loader import load_config


def test_defaults_when_no_env():
    cfg = load_config({})
    assert cfg["db_port"] == 5432
    assert cfg["db_host"] == "localhost"
    assert cfg["debug"] is False
    assert cfg["timeout"] == 30


def test_unrelated_env_ignored():
    cfg = load_config({"PATH": "/usr/bin", "HOME": "/root"})
    assert cfg["db_port"] == 5432
