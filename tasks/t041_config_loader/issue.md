# Bug: environment overrides are sometimes ignored

Setting `CONFIG_DB_PORT=6000` still yields the default `5432` from
`load_config(env)`. The precedence we want is **env > file > defaults** for
every key, and override values must come out with the right type (`db_port` as
an `int`, `debug` as a `bool`), not as raw strings.

`load_config({})` correctly returns the defaults. Unrelated environment
variables must keep being ignored.
