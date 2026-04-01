"""Project configuration and feature flags."""

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FeatureFlags:
    """Typed feature flags for progressive rollouts."""

    premium: bool = _as_bool(os.getenv("FEATURE_PREMIUM"), default=False)
    analytics: bool = _as_bool(os.getenv("FEATURE_ANALYTICS"), default=False)


FEATURE_FLAGS = FeatureFlags()
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///./tele_manager.db", alias="DATABASE_URL")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    return Settings()
