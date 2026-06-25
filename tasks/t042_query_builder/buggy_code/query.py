def build_select(table, where, dialect):
    keys = list(where.keys())
    params = [where[k] for k in keys]
    clauses = [f"{k} = ?" for k in keys]
    sql = f"SELECT * FROM {table}"  # noqa: S608
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return sql, params


def build_where_in(column, values, dialect):
    values = list(values)
    holders = ", ".join("?" for _ in values)
    return f"{column} IN ({holders})", values
