class SQLiteDialect:
    def placeholder(self, index):
        return "?"


class PostgresDialect:
    def placeholder(self, index):
        return f"${index}"


def _build(cond, dialect, counter):
    typ = cond[0]
    if typ == "eq":
        _, col, val = cond
        ph = dialect.placeholder(counter[0])
        counter[0] += 1
        return f"{col} = {ph}", [val]
    if typ == "in":
        _, col, vals = cond
        vals = list(vals)
        holders = []
        for _ in vals:
            holders.append(dialect.placeholder(counter[0]))
            counter[0] += 1
        return f"{col} IN ({', '.join(holders)})", vals
    if typ in ("and", "or"):
        _, subs = cond
        parts = []
        params = []
        for sub in subs:
            sql, sub_params = _build(sub, dialect, counter)
            parts.append(f"({sql})")
            params.extend(sub_params)
        joiner = " AND " if typ == "and" else " OR "
        return joiner.join(parts), params
    raise ValueError(f"unknown condition: {typ}")


def build(cond, dialect=None):
    dialect = dialect or SQLiteDialect()
    return _build(cond, dialect, [1])
