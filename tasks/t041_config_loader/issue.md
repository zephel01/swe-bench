# Bug: config layering is wrong on two fronts

`load_config(env, file_config)` combines three sources. Two things are wrong:

- **Precedence**: when a key is set in both the file and the environment, the
  file value wins. The order must be **env > file > defaults**.
- **Typing**: values coming from the *file* layer are left as raw strings; only
  environment values get coerced. Every value whose key has a typed default
  must be coerced (`int`, `bool`, `float`), regardless of which layer it came
  from.

Defaults-only and env-only overrides already work.
