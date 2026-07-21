# Refactor: unify the `User` identifier type to `str`

The `User` identifier is inconsistent across the four files that make up
the user module (`model.py`, `repo.py`, `service.py`, `api.py`), which
lets the same logical user end up under two different keys and quietly
breaks `get` / `exists`.

## Current state

- `model.User.id` is annotated as `int`.
- `repo.UserRepo` uses `int` keys internally, and `get` / `exists` are
  annotated as taking `int`.
- `service.UserService` methods have **unannotated** `id` parameters and
  end up mixing `str` and `int` values depending on the caller.
- `api.API.create` reads `payload["id"]` and forwards it as-is. Callers
  in the wild pass both `int` and `str`, so the same user can be stored
  under `1` (int) *and* `"1"` (str) — a subsequent `get` / `exists` with
  the "wrong" type silently misses.

## Desired state

Unify the internal identifier to `str` (UUID-style) end-to-end:

- `User.id: str`.
- `UserRepo.save` / `get` / `exists` require `str` ids and use `str`
  keys. Non-`str` ids MUST raise `TypeError` at the boundary
  (explicit `isinstance` check).
- `UserService.register` / `find` / `is_registered` declare
  `id: str` and require `str`.
- `api.API` keeps backwards compatibility with existing clients: both
  `create` (via `payload["id"]`) and `get` MUST accept either `int` or
  `str`, and normalize to `str` (`str(id)`) before calling into the
  service. Annotate `API.get`'s `id` parameter as `Union[int, str]`
  (a.k.a. `int | str`).

Fixing only one or two of the four files will leave either
`test_bug.py` or `test_consistency.py` red — every file above has to
line up.
