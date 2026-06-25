def build(cond):
    typ = cond[0]
    if typ == "eq":
        _, col, val = cond
        return f"{col} = ?", [val]
    if typ == "in":
        _, col, vals = cond
        vals = list(vals)
        holders = ", ".join("?" for _ in vals)
        return f"{col} IN ({holders})", vals
    if typ in ("and", "or"):
        _, subs = cond
        parts = []
        params = []
        for sub in subs:
            sql, sub_params = build(sub)
            parts.append(f"({sql})")
            params.extend(sub_params)
        joiner = " AND " if typ == "and" else " OR "
        return joiner.join(parts), params
    raise ValueError(f"unknown condition: {typ}")
