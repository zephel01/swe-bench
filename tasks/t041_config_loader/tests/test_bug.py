from loader import load_config


def test_env_beats_file_for_same_key():
    cfg = load_config({"CONFIG_DB_PORT": "6000"}, {"db_port": 7000})
    assert cfg["db_port"] == 6000


def test_file_used_when_env_absent():
    cfg = load_config({}, {"db_host": "db.internal"})
    assert cfg["db_host"] == "db.internal"


def test_file_beats_defaults():
    cfg = load_config({}, {"db_port": 7000})
    assert cfg["db_port"] == 7000


def test_three_layers_with_coercion():
    cfg = load_config(
        {"CONFIG_DEBUG": "true"},
        {"debug": False, "timeout": 99, "db_host": "filehost"},
    )
    assert cfg["debug"] is True          # env wins over file
    assert cfg["timeout"] == 99          # file wins over default
    assert cfg["db_host"] == "filehost"  # file wins over default
    assert cfg["db_port"] == 5432        # default
