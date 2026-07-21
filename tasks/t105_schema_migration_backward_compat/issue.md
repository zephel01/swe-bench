# Migrate `User.name` to `first_name` / `last_name` with backward compatibility

## Problem

`User` currently stores a single `name: str`. Product wants to split it into
`first_name` and `last_name`. We must not break existing code or existing data:

- Existing callers use `save_user(user, path)` and `load_user(path)`; their
  signatures must not change.
- Persistent JSON files already on disk use the legacy shape
  `{"name": "Alice Wonder"}`. `load_user` must transparently migrate them.
- New writes emit the new shape `{"first_name": ..., "last_name": ...}`, and
  `load_user` must also read that shape back.
- Legacy code still does `user.name` — the resulting `User` must expose a
  `name` property that returns `f"{first_name} {last_name}"` (trimmed).
- A `migrate_legacy(record: dict) -> dict` helper must be public so external
  batch migrators can reuse the same split rule.

## Acceptance

- `User` is a dataclass with `first_name: str` and `last_name: str`, plus a
  `name` property that concatenates them.
- `save_user(user, path)` writes only the new schema.
- `load_user(path)` accepts either schema. When it sees the legacy schema it
  runs `migrate_legacy`, then constructs the `User`.
- `migrate_legacy({"name": "Alice Wonder"})` returns
  `{"first_name": "Alice", "last_name": "Wonder"}`.
- Single-word legacy names split to `first_name=<name>, last_name=""`.
- Records already in the new schema pass through `migrate_legacy` unchanged.
