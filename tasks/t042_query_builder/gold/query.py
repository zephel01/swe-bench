def build_select(table, where, dialect):
    keys = list(where.keys())
    params = [where[k] for k in keys]
    clauses = [f"{k} = {dialect.placeholder(i)}" for i, k in enumerate(keys, 1)]
    sql = f"SELECT * FROM {table}"  # noqa: S608
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return sql, params


def build_where_in(column, values, dialect):
    values = list(values)
    holders = ", ".join(dialect.placeholder(i) for i in range(1, len(values) + 1))
    return f"{column} IN ({holders})", values
