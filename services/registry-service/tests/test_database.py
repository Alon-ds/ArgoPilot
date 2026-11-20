"""Database portability, seed preservation and configuration regression tests."""
import runpy
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

import database
import seed
from config import Settings
from pydantic import ValidationError


def test_seed_empty_database_and_refuse_overwrite(tmp_path):
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    with patch.object(database.settings, "database_url", url):
        runpy.run_module("seed", run_name="__main__")
        with database.connect_database() as connection:
            counts = [connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in ("farms", "plots", "crops", "soils", "emitters")]
            assert counts == [2, 4, 2, 3, 4]
        with pytest.raises(SQLAlchemyError):
            runpy.run_module("seed", run_name="__main__")
        with database.connect_database() as connection:
            assert connection.execute("SELECT COUNT(*) FROM plots").fetchone()[0] == 4


def test_postgres_url_and_transaction_selection():
    fake_engine = MagicMock()
    fake_engine.dialect.name = "postgresql"
    with patch.object(database, "create_engine", return_value=fake_engine) as factory:
        assert database.database_engine("postgresql://user:password@localhost/registry") is fake_engine
        assert factory.call_args.args[0].drivername == "postgresql+psycopg"
    connection = MagicMock()
    connection.dialect.name = "postgresql"
    assert database.Connection(connection).execute("BEGIN IMMEDIATE") is None
    connection.execute.assert_not_called()


def test_settings_and_sqlite_engine():
    assert Settings(_env_file=None, database_url="sqlite://").database_url == "sqlite://"
    for invalid in ("not-a-url", "mysql://localhost/database"):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, database_url=invalid)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        row = database.Connection(connection).execute("SELECT 7 AS value").fetchone()
        assert row["value"] == row[0] == 7
    engine.dispose()


def test_missing_required_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)
