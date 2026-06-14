"""パラメータ化SQLを組み立てるクエリビルダ (インジェクション安全)."""

from __future__ import annotations

from dialect import PLACEHOLDER


class Query:
    def __init__(self, table: str) -> None:
        self.table = table
        self._cols = ["*"]
        self._where: list[str] = []
        self._params: list = []

    def select(self, *cols: str) -> Query:
        if cols:
            self._cols = list(cols)
        return self

    def where(self, col: str, op: str, value) -> Query:
        self._where.append(f"{col} {op} {PLACEHOLDER}")
        self._params.append(value)
        return self

    def where_in(self, col: str, values: list) -> Query:
        marks = ", ".join(PLACEHOLDER for _ in values)
        self._where.append(f"{col} IN ({marks})")
        self._params.extend(values)
        return self

    def build(self) -> tuple[str, list]:
        sql = f"SELECT {', '.join(self._cols)} FROM {self.table}"  # noqa: S608
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        return sql, list(self._params)
