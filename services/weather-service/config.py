"""All deployment settings. No other service's configuration is imported."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    open_meteo_base_url: AnyHttpUrl = "https://api.open-meteo.com"
    open_meteo_api_key: SecretStr = SecretStr("")
    forecast_timezone: str = "Asia/Jerusalem"
    provider_timeout_seconds: float = Field(default=5.0, gt=0, allow_inf_nan=False)
    provider_retries: int = Field(default=2, ge=0, le=10)
    cache_freshness_seconds: int = Field(default=10800, gt=0)
    stale_max_age_seconds: int = Field(default=86400, gt=0)
    retry_after_seconds: int = Field(default=60, gt=0)

    @field_validator("forecast_timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("FORECAST_TIMEZONE must name an installed IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def check_age_limits(self):
        if self.stale_max_age_seconds < self.cache_freshness_seconds:
            raise ValueError("STALE_MAX_AGE_SECONDS must be >= CACHE_FRESHNESS_SECONDS")
        return self
