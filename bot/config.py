"""Project configuration and feature flags."""

import logging
import os
from dataclasses import dataclass


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


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    return Settings()


def validate_required_env_vars() -> None:
    required_env_vars = ["BOT_TOKEN", "DATABASE_URL"]
    missing = [name for name in required_env_vars if not os.getenv(name)]
    if missing:
        missing_list = ", ".join(missing)
        logger.critical("Missing required environment variables: %s", missing_list)
        raise RuntimeError(f"Missing required environment variables: {missing_list}")
