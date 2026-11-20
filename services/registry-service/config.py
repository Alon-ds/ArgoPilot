"""Validated environment configuration; secrets are never logged."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: str

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value):
        try:
            parsed = make_url(value)
        except ArgumentError as error:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from error
        if parsed.get_backend_name() not in {"sqlite", "postgresql"}:
            raise ValueError("DATABASE_URL must select SQLite or PostgreSQL")
        return value


settings = Settings()
