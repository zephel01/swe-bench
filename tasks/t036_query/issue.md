# Bug: where_in puts raw values into the SQL text

`Query("t").where_in("id", [10, 20, 30]).build()` returns
`("SELECT * FROM t WHERE id IN (10, 20, 30)", [])` — the values are baked into the
SQL string and the params list is empty. Every value should be passed as a bound
parameter instead, i.e. `("... id IN (?, ?, ?)", [10, 20, 30])`.

Single `where`, column selection and `AND` joining are correct.
