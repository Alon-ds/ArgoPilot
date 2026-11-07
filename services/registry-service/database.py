"""SQLite connections for the registry service."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "registry.db"


@contextmanager
def connect_database(path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Open an existing database, commit on success, and always close it."""
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()
