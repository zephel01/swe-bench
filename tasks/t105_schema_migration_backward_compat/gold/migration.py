"""Legacy-to-new schema migration for User records."""
from __future__ import annotations


def migrate_legacy(record: dict) -> dict:
    """Convert a legacy `{"name": ...}` record to the new two-field schema.

    Records already in the new schema (both `first_name` and `last_name`
    present) are returned as a shallow copy, unchanged. Single-word legacy
    names split to `first_name=<name>, last_name=""`.
    """
    if "first_name" in record and "last_name" in record:
        return dict(record)
    if "name" in record:
        parts = str(record["name"]).split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        out = {k: v for k, v in record.items() if k != "name"}
        out["first_name"] = first
        out["last_name"] = last
        return out
    raise KeyError(
        "record must have either 'name' or both 'first_name' and 'last_name'"
    )
