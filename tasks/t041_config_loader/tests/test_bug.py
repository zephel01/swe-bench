from loader import load_config


def test_env_beats_file():
    cfg = load_config({"CONFIG_DB_PORT": "6000"}, {"db_port": 7000})
    assert cfg["db_port"] == 6000


def test_file_value_is_coerced():
    # a string value coming from the file layer must also be typed
    cfg = load_config({}, {"db_port": "7000"})
    assert cfg["db_port"] == 7000
    assert isinstance(cfg["db_port"], int)


def test_three_layers_combined():
    cfg = load_config(
        {"CONFIG_DEBUG": "true"},
        {"debug": "false", "timeout": "99"},
    )
    assert cfg["debug"] is True       # env > file
    assert cfg["timeout"] == 99       # file coerced over default
    assert isinstance(cfg["timeout"], int)
    assert cfg["db_port"] == 5432     # default
