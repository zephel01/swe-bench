def build_select(table, where, dialect, in_clause=None):
    params = []
    clauses = []
    for key in where:
        clauses.append(f"{key} = {dialect.placeholder(1)}")
        params.append(where[key])
    if in_clause:
        col, values = in_clause
        values = list(values)
        holders = ", ".join("?" for _ in values)
        clauses.append(f"{col} IN ({holders})")
        params.extend(values)
    sql = f"SELECT * FROM {table}"  # noqa: S608
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return sql, params
