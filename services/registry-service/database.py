"""SQLAlchemy connections for SQLite development and PostgreSQL production."""
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from functools import lru_cache
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from config import settings


DATABASE_PATH = Path(__file__).resolve().parent / "registry.db"


@lru_cache(maxsize=32)
def database_engine(url: str):
    parsed = make_url(url)
    if parsed.drivername == "postgresql":
        url = parsed.set(drivername="postgresql+psycopg")
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys = ON")
    return engine


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Result:
    def __init__(self, result):
        self.result = result

    def fetchone(self):
        row = self.result.mappings().fetchone()
        return None if row is None else Row(row)

    def fetchall(self):
        return [Row(row) for row in self.result.mappings().all()]

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters=()):
        if statement == "BEGIN IMMEDIATE" and self.connection.dialect.name != "sqlite":
            return None  # engine.begin() already owns the PostgreSQL transaction.
        pieces = statement.split("?")
        query = pieces[0] + "".join(f":p{i}{part}" for i, part in enumerate(pieces[1:]))
        bindings = {f"p{i}": value for i, value in enumerate(parameters)}
        return Result(self.connection.execute(text(query), bindings))


@contextmanager
def connect_database(path: Path | None = None) -> Iterator[Connection]:
    url = settings.database_url
    if path is not None:
        url = "sqlite:///file:" + str(path.resolve()) + "?mode=rw&uri=true"
    with database_engine(url).begin() as connection:
        yield Connection(connection)
