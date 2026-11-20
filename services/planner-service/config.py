"""All deployment-dependent planner settings."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    registry_url: AnyHttpUrl
    weather_url: AnyHttpUrl
    upstream_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)
    planner_timezone: str = "Asia/Jerusalem"

    @field_validator("planner_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("PLANNER_TIMEZONE must be an IANA timezone") from exc
        return value
