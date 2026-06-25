# Bug: config layer precedence is wrong (env vs file)

`load_config(env, file_config)` layers three sources. The intended precedence is
**env > file > defaults** for every key, with override values coerced to the
declared type (`db_port` as `int`, `debug` as `bool`).

Observed: when the same key is set in both a config file and an environment
variable, the **file value wins** — e.g. `CONFIG_DB_PORT=6000` with a file
`{"db_port": 7000}` yields `7000`, but it must be `6000`. Env-only overrides and
file-only values work; defaults fill the rest.
