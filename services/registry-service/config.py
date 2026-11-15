"""Registry database configuration."""

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


SERVICE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = SERVICE_DIR / "registry.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVICE_DIR / ".env", extra="ignore", hide_input_in_errors=True
    )

    database_url: Annotated[URL, NoDecode] = Field(
        default_factory=lambda: URL.create("sqlite", database=str(DATABASE_PATH))
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def parse_database_url(cls, value: str | URL) -> URL:
        try:
            url = make_url(value)
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid database URL.") from None

        if url.drivername in {"postgresql", "postgresql+psycopg"} and url.database:
            return url.set(drivername="postgresql+psycopg")
        if url.drivername in {"sqlite", "sqlite+pysqlite"} and url.database not in {None, "", ":memory:"}:
            path = SERVICE_DIR / url.database
            return url.set(drivername="sqlite", database=str(path.resolve()))
        raise ValueError("DATABASE_URL must select a SQLite file or a PostgreSQL database.")
