class Dialect:
    def placeholder(self, index):
        raise NotImplementedError


class SQLiteDialect(Dialect):
    def placeholder(self, index):
        return "?"


class PostgresDialect(Dialect):
    def placeholder(self, index):
        return f"${index}"
