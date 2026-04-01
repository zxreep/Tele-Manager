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
