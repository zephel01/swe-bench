from loader import load_config


def test_int_override_typed():
    cfg = load_config({"CONFIG_DB_PORT": "6000"})
    assert cfg["db_port"] == 6000
    assert isinstance(cfg["db_port"], int)


def test_str_override():
    cfg = load_config({"CONFIG_DB_HOST": "db.internal"})
    assert cfg["db_host"] == "db.internal"


def test_bool_override():
    cfg = load_config({"CONFIG_DEBUG": "true"})
    assert cfg["debug"] is True


def test_partial_override_keeps_other_defaults():
    cfg = load_config({"CONFIG_DB_PORT": "7000"})
    assert cfg["db_port"] == 7000
    assert cfg["db_host"] == "localhost"
