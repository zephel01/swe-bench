def build_select(table, where, dialect, in_clause=None):
    params = []
    clauses = []
    index = 1
    for key in where:
        clauses.append(f"{key} = {dialect.placeholder(index)}")
        params.append(where[key])
        index += 1
    if in_clause:
        col, values = in_clause
        values = list(values)
        holders = []
        for value in values:
            holders.append(dialect.placeholder(index))
            params.append(value)
            index += 1
        clauses.append(f"{col} IN ({', '.join(holders)})")
    sql = f"SELECT * FROM {table}"  # noqa: S608
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return sql, params
