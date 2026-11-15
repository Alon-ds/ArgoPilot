"""Engine selection and transactions for the Registry."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from pathlib import Path

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from config import Settings


def create_registry_engine(database_url: URL | str, *, create: bool = False) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "postgresql":
        return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})

    path = Path(url.database)
    url = url.set(database=path.as_uri()).update_query_dict(
        {"mode": "rwc" if create else "rw", "uri": "true"}
    )
    # Reopen the path each time so a restored database takes effect immediately.
    engine = create_engine(url, poolclass=NullPool)

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys = ON").close()

    @event.listens_for(engine, "begin")
    def begin_sqlite(connection):
        # Serialize the read/validate/write sequence for SQLite writers.
        statement = "BEGIN IMMEDIATE" if connection.get_execution_options().get("registry_write") else "BEGIN"
        connection.exec_driver_sql(statement)

    return engine


@cache
def get_engine() -> Engine:
    return create_registry_engine(Settings().database_url)


@contextmanager
def connect_database(*, write: bool = False) -> Iterator[Connection]:
    """Return one connection and commit or roll back its transaction."""
    with get_engine().connect() as connection:
        connection.execution_options(registry_write=write)
        with connection.begin():
            yield connection
