import copy

from confmerge import merge_config
from defaults import DEFAULT_CONFIG


def test_nested_merge_keeps_siblings():
    merged = merge_config(DEFAULT_CONFIG, {"db": {"port": 5433}})
    assert merged["db"]["port"] == 5433
    assert merged["db"]["host"] == "localhost"
    assert merged["db"]["options"]["timeout"] == 30


def test_deep_merge():
    merged = merge_config(DEFAULT_CONFIG, {"db": {"options": {"ssl": True}}})
    assert merged["db"]["options"] == {"timeout": 30, "ssl": True}


def test_replace_non_dict():
    merged = merge_config(DEFAULT_CONFIG, {"log": {"handlers": ["file"]}})
    assert merged["log"]["handlers"] == ["file"]
    assert merged["log"]["level"] == "INFO"


def test_no_mutation():
    snapshot = copy.deepcopy(DEFAULT_CONFIG)
    merge_config(DEFAULT_CONFIG, {"db": {"port": 9999}, "debug": True})
    assert DEFAULT_CONFIG == snapshot


def test_new_key():
    merged = merge_config(DEFAULT_CONFIG, {"cache": {"ttl": 60}})
    assert merged["cache"] == {"ttl": 60}
    assert merged["debug"] is False
