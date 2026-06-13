# Bug: overriding one nested key erases its siblings

`merge_config(DEFAULT_CONFIG, {"db": {"port": 5433}})` should keep
`db.host` from the defaults, but the whole `db` section is replaced and
`host` disappears. Nested dicts must be merged recursively; non-dict
values (including lists) are replaced. The inputs must NOT be mutated.
Files: `defaults.py` (default config, correct) and `confmerge.py`.
