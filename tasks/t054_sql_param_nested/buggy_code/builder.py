class SQLiteDialect:
    def placeholder(self, index):
        return "?"


class PostgresDialect:
    def placeholder(self, index):
        return f"${index}"


def _literal(value):
    if isinstance(value, str):
        return "'" + value + "'"
    return str(value)


def _render(cond):
    typ = cond[0]
    if typ == "eq":
        _, col, val = cond
        return f"{col} = {_literal(val)}"
    if typ == "in":
        _, col, vals = cond
        return f"{col} IN ({', '.join(_literal(v) for v in vals)})"
    if typ in ("and", "or"):
        _, subs = cond
        joiner = " AND " if typ == "and" else " OR "
        return joiner.join(f"({_render(s)})" for s in subs)
    raise ValueError(f"unknown condition: {typ}")


def build(cond, dialect=None):
    typ = cond[0]
    if typ == "eq":
        _, col, val = cond
        return f"{col} = ?", [val]
    if typ == "in":
        _, col, vals = cond
        vals = list(vals)
        holders = ", ".join("?" for _ in vals)
        return f"{col} IN ({holders})", vals
    return _render(cond), []
